#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Benchmark persistente con LOGS de Redis:
- Permite capturar N usuarios manualmente o autogenerarlos
- Inserta y lee en MariaDB (tabla users) y en Redis (hashes)
- Mide tiempos con time.time()
- NO limpia (persistente)
- Muestra "logs" de comandos Redis usados (HSET, SADD, HGETALL, EXEC)
"""

import sys
import time
import uuid
import getpass
from typing import List, Tuple

try:
    import pymysql
except ImportError:
    print("Falta PyMySQL. Instálalo con: pip install PyMySQL", file=sys.stderr)
    sys.exit(1)

try:
    import redis
except ImportError:
    print("Falta redis (redis-py). Instálalo con: pip install redis", file=sys.stderr)
    sys.exit(1)


# ------------------------------ Utilidades de input ------------------------------

def prompt_with_default(prompt_text: str, default: str) -> str:
    v = input(f"{prompt_text} [{default}]: ").strip()
    return v if v else default


def prompt_secret_with_default(prompt_text: str, default: str) -> str:
    v = getpass.getpass(f"{prompt_text} (dejar vacío para usar por defecto): ")
    return v if v else default


def si_no(prompt_text: str, default_yes: bool = False) -> bool:
    d = "S/n" if default_yes else "s/N"
    v = input(f"{prompt_text} ({d}): ").strip().lower()
    if v == "" and default_yes:
        return True
    return v in ("s", "si", "sí", "y", "yes")


# ------------------------------ Conexiones ------------------------------

def connect_mysql(host: str, port: int, user: str, password: str, db: str):
    return pymysql.connect(
        host=host, port=port, user=user, password=password, database=db,
        autocommit=False, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def connect_redis(host: str, port: int, db: int, password: str = None):
    return redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)


# ------------------------------ Verificaciones MySQL ------------------------------

def check_users_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS n
            FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = 'users';
        """)
        if cur.fetchone()["n"] == 0:
            raise RuntimeError("La tabla 'users' no existe en la base seleccionada.")


def ensure_batches_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bench_batches (
            id VARCHAR(32) PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            n_insertados INT NOT NULL,
            notas VARCHAR(255) NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
    conn.commit()


# ------------------------------ Preparación de datos ------------------------------

def capture_users_manual(n: int, batch_id: str) -> List[Tuple[str, str, str]]:
    print("\nCaptura manual de usuarios (email, username, password_hash).")
    print("Tip: si no tienes hash real, puedes poner un texto cualquiera.\n")
    rows = []
    for i in range(n):
        print(f"Usuario {i+1}/{n}")
        email = input("  email: ").strip()
        username = input("  username: ").strip()
        password_hash = input("  password_hash: ").strip()
        if not email or not username or not password_hash:
            print("  [WARN] Campos vacíos; se autogenerarán valores de fallback.")
            u = uuid.uuid4().hex[:12]
            email = email or f"bench_{batch_id}_{i}_{u}@example.com"
            username = username or f"bench_{batch_id}_{i}_{u}"
            password_hash = password_hash or f"sha256:{uuid.uuid4().hex}"
        rows.append((email, username, password_hash))
    return rows


def prepare_mysql_batch(batch_id: str, n: int) -> List[Tuple[str, str, str]]:
    rows = []
    for i in range(n):
        u = uuid.uuid4().hex[:12]
        email = f"bench_{batch_id}_{i}_{u}@example.com"
        username = f"bench_{batch_id}_{i}_{u}"
        password_hash = f"sha256:{uuid.uuid4().hex}"
        rows.append((email, username, password_hash))
    return rows


# ------------------------------ MySQL ops ------------------------------

def mysql_insert(conn, rows: List[Tuple[str, str, str]]) -> Tuple[float, List[int]]:
    t0 = time.time()
    ids = []
    with conn.cursor() as cur:
        sql = "INSERT INTO users (email, username, password_hash) VALUES (%s, %s, %s)"
        for r in rows:
            cur.execute(sql, r)
            ids.append(cur.lastrowid)
    conn.commit()
    t1 = time.time()
    return (t1 - t0), ids


def mysql_read(conn, ids: List[int]) -> float:
    if not ids:
        return 0.0
    t0 = time.time()
    with conn.cursor() as cur:
        fmt = ",".join(["%s"] * len(ids))
        cur.execute(f"SELECT id, email, username, created_at FROM users WHERE id IN ({fmt})", ids)
        _ = cur.fetchall()
    t1 = time.time()
    return t1 - t0


def mysql_record_batch(conn, batch_id: str, n: int, notas: str = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO bench_batches (id, n_insertados, notas) VALUES (%s,%s,%s)",
            (batch_id, n, notas),
        )
    conn.commit()


# ------------------------------ Redis Logging Wrapper ------------------------------

class RedisLog:
    """
    Wrapper mínimo para llevar "logs" legibles de los comandos ejecutados en Redis.
    No reemplaza a redis.Redis; solo registra lo que hacemos con pipeline.
    """
    def __init__(self, client: redis.Redis):
        self.client = client
        self.logs = []  # lista de strings

    def pipeline(self):
        return LoggedPipeline(self)

    def ping(self):
        # Log de prueba de conexión
        self.logs.append("PING")
        return self.client.ping()

    def print_summary(self):
        if not self.logs:
            print("\n[REDIS LOG] No se registraron comandos.")
            return

        print("\n=== REDIS LOG (resumen) ===")
        # Conteo por comando
        counts = {}
        examples = {}
        for line in self.logs:
            cmd = line.split(" ", 1)[0]
            counts[cmd] = counts.get(cmd, 0) + 1
            if cmd not in examples and len(line) < 200:
                examples[cmd] = line

        for cmd in sorted(counts.keys()):
            print(f"- {cmd}: {counts[cmd]}")
            if cmd in examples:
                print(f"  ej: {examples[cmd]}")
        print("===========================")


class LoggedPipeline:
    """
    Envuelve un pipeline real y registra llamadas.
    """
    def __init__(self, rlog: RedisLog):
        self.rlog = rlog
        self.pipe = rlog.client.pipeline()

    def hset(self, name, mapping=None, **kwargs):
        # registro legible
        self.rlog.logs.append(f"HSET {name} FIELDS={list((mapping or kwargs).keys())}")
        return self.pipe.hset(name, mapping=mapping, **kwargs)

    def sadd(self, name, *values):
        preview = values[:3]
        extra = "" if len(values) <= 3 else f"...(+{len(values)-3})"
        self.rlog.logs.append(f"SADD {name} VALUES_PREVIEW={preview}{extra}")
        return self.pipe.sadd(name, *values)

    def hgetall(self, name):
        self.rlog.logs.append(f"HGETALL {name}")
        return self.pipe.hgetall(name)

    def execute(self):
        self.rlog.logs.append("EXEC (pipeline.execute)")
        return self.pipe.execute()


# ------------------------------ Redis ops (con logs) ------------------------------

def redis_insert(rlog: RedisLog, batch_id: str, rows: List[Tuple[str, str, str]]) -> Tuple[float, List[str]]:
    keys = []
    pipe = rlog.pipeline()
    t0 = time.time()
    created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    batch_set_key = f"batch:{batch_id}:keys"

    for i, (email, username, password_hash) in enumerate(rows):
        k = f"user:{batch_id}:{i}:{uuid.uuid4().hex[:8]}"
        keys.append(k)
        pipe.hset(k, mapping={
            "email": email,
            "username": username,
            "password_hash": password_hash,
            "created_at": created_at
        })
        pipe.sadd(batch_set_key, k)

    # índice global de batches
    pipe.sadd("batches:index", batch_id)
    pipe.execute()
    t1 = time.time()
    return (t1 - t0), keys


def redis_read(rlog: RedisLog, keys: List[str]) -> float:
    pipe = rlog.pipeline()
    t0 = time.time()
    for k in keys:
        pipe.hgetall(k)
    _ = pipe.execute()
    t1 = time.time()
    return t1 - t0


# ------------------------------ Main ------------------------------

def main():
    print("=== Benchmark (persistente + logs Redis) ===")

    # Defaults
    default_mysql_host = "127.0.0.1"
    default_mysql_port = "3306"
    default_mysql_user = "libros_user"
    default_mysql_pass = "666"
    default_mysql_db   = "Libros"

    default_redis_host = "127.0.0.1"
    default_redis_port = "6379"
    default_redis_db   = "0"
    default_redis_pass = ""

    # ---- Inputs
    print("\n-- Datos de MariaDB --")
    m_host = prompt_with_default("Host", default_mysql_host)
    m_port = int(prompt_with_default("Puerto", default_mysql_port))
    m_user = prompt_with_default("Usuario", default_mysql_user)
    m_pass = prompt_secret_with_default("Contraseña", default_mysql_pass)
    m_db   = prompt_with_default("Base de datos", default_mysql_db)

    print("\n-- Datos de Redis --")
    r_host = prompt_with_default("Host", default_redis_host)
    r_port = int(prompt_with_default("Puerto", default_redis_port))
    r_db   = int(prompt_with_default("DB (índice)", default_redis_db))
    r_pass = prompt_secret_with_default("Contraseña", default_redis_pass)

    n_records = int(prompt_with_default("\nCantidad de usuarios a insertar/leer (N)", "5"))
    captura_manual = si_no("¿Captura manual de usuarios?", False)
    notas = prompt_with_default("Notas para identificar este batch (opcional)", "")

    batch_id = uuid.uuid4().hex[:10]
    print(f"\n[INFO] Batch ID: {batch_id}")

    # ---- Conexiones
    try:
        mysql_conn = connect_mysql(m_host, m_port, m_user, m_pass, m_db)
    except Exception as e:
        print(f"[ERROR] Conexión a MariaDB falló: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        rcli = connect_redis(r_host, r_port, r_db, r_pass if r_pass else None)
        rlog = RedisLog(rcli)
        rlog.ping()
    except Exception as e:
        print(f"[ERROR] Conexión a Redis falló: {e}", file=sys.stderr)
        mysql_conn.close()
        sys.exit(3)

    # ---- Verificaciones y preparación
    try:
        check_users_table(mysql_conn)
    except Exception as e:
        print(f"[ERROR] Verificación 'users' falló: {e}", file=sys.stderr)
        mysql_conn.close()
        sys.exit(4)

    ensure_batches_table(mysql_conn)

    if captura_manual:
        rows = capture_users_manual(n_records, batch_id)
    else:
        rows = prepare_mysql_batch(batch_id, n_records)

    # ---- MySQL: INSERT + READ
    try:
        t_ins_mysql, ids = mysql_insert(mysql_conn, rows)
        t_read_mysql = mysql_read(mysql_conn, ids)
        mysql_record_batch(mysql_conn, batch_id, len(ids), notas if notas else None)
    except Exception as e:
        print(f"[ERROR] Operaciones MySQL fallaron: {e}", file=sys.stderr)
        mysql_conn.close()
        sys.exit(5)

    # ---- Redis: INSERT + READ (con logs)
    try:
        t_ins_redis, redis_keys = redis_insert(rlog, batch_id, rows)
        t_read_redis = redis_read(rlog, redis_keys)
    except Exception as e:
        print(f"[ERROR] Operaciones Redis fallaron: {e}", file=sys.stderr)
        mysql_conn.close()
        sys.exit(6)

    # ---- Resultados
    print("\n=== RESULTADOS (segundos) ===")
    print(f"MariaDB  -> Insertar {n_records}: {t_ins_mysql:.6f} s")
    print(f"MariaDB  -> Leer     {len(ids)}: {t_read_mysql:.6f} s")
    print(f"Redis    -> Insertar {n_records}: {t_ins_redis:.6f} s")
    print(f"Redis    -> Leer     {len(redis_keys)}: {t_read_redis:.6f} s")

    def ratio(a, b) -> str:
        try:
            return f"{a/b:.2f}x"
        except ZeroDivisionError:
            return "∞"

    print("\n=== COMPARATIVA (aprox) ===")
    print(f"Insert Redis / Insert MariaDB: {ratio(t_ins_redis, t_ins_mysql)}")
    print(f"Leer   Redis / Leer   MariaDB: {ratio(t_read_redis, t_read_mysql)}")

    # ---- Log Redis (resumen de funciones usadas)
    rlog.print_summary()

    # ---- Indicadores de persistencia
    print("\n=== PERSISTENCIA ===")
    print(f"- Batch ID: {batch_id}")
    print(f"- Redis índice global de batches: 'batches:index'")
    print(f"- Redis set de keys del batch: 'batch:{batch_id}:keys'")
    print(f"- MySQL tabla batches: bench_batches (id={batch_id})")
    print("\nNo se eliminó nada. ✔\n")

    mysql_conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado por el usuario.", file=sys.stderr)
        sys.exit(130)
