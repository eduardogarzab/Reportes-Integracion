#!usrbinenv python3
# -- coding utf-8 --

Benchmark simple Redis (hashes) vs MariaDB (tabla users)
- Solicita credenciales al usuario (con valores por defecto proporcionados)
- Inserta y lee N registros en ambos DBMS
- Mide tiempos con time.time()
- Usa hashes en Redis
- Limpia los datos insertados al final

Tablas asumidas (según dump provisto) base 'Libros', tabla 'users' con
  id BIGINT UNSIGNED AUTO_INCREMENT PK,
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(60) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP


import sys
import time
import uuid
import getpass
from typing import List, Tuple

try
    import pymysql
except ImportError
    print(Falta PyMySQL. Instálalo con pip install PyMySQL, file=sys.stderr)
    sys.exit(1)

try
    import redis
except ImportError
    print(Falta redis (redis-py). Instálalo con pip install redis, file=sys.stderr)
    sys.exit(1)


def prompt_with_default(prompt_text str, default str) - str
    v = input(f{prompt_text} [{default}] ).strip()
    return v if v else default


def prompt_secret_with_default(prompt_text str, default str) - str
    v = getpass.getpass(f{prompt_text} (dejar vacío para usar por defecto) )
    return v if v else default


def connect_mysql(host str, port int, user str, password str, db str)
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        autocommit=False,  # control explícito de transacciones
        charset=utf8mb4,
        cursorclass=pymysql.cursors.DictCursor,
    )


def connect_redis(host str, port int, db int, password str = None)
    return redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)


def check_users_table(conn) - None
    with conn.cursor() as cur
        cur.execute(
            SELECT COUNT() AS n
            FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = 'users';
        )
        if cur.fetchone()[n] == 0
            raise RuntimeError(La tabla 'users' no existe en la base seleccionada. 
                               Importa el dump o corrige el nombre de la BD.)


def prepare_mysql_batch(conn, batch_id str, n int) - List[Tuple[str, str, str]]
    
    Genera N tuplas (email, username, password_hash) únicas.
    password_hash aquí es un placeholder; en prod deberías usar un hash seguro (bcryptargon2).
    
    rows = []
    for i in range(n)
        # Sufijos únicos por batch
        u = uuid.uuid4().hex[12]
        email = fbench_{batch_id}_{i}_{u}@example.com
        username = fbench_{batch_id}_{i}_{u}
        password_hash = fsha256{uuid.uuid4().hex}  # marcador simple
        rows.append((email, username, password_hash))
    return rows


def mysql_insert(conn, rows List[Tuple[str, str, str]]) - Tuple[float, List[int]]
    
    Inserta filas en users y devuelve (tiempo_segundos, [ids_insertados])
    
    t0 = time.time()
    ids = []
    with conn.cursor() as cur
        sql = 
            INSERT INTO users (email, username, password_hash)
            VALUES (%s, %s, %s)
        
        for r in rows
            cur.execute(sql, r)
            ids.append(cur.lastrowid)
    conn.commit()
    t1 = time.time()
    return (t1 - t0), ids


def mysql_read(conn, ids List[int]) - float
    
    Lee por id; devuelve tiempo en segundos para traer todos.
    
    t0 = time.time()
    with conn.cursor() as cur
        # Eficiente leer en bloque
        if not ids
            return 0.0
        # evitar lista demasiado grande en casos reales — aquí está bien para demo
        fmt = ,.join([%s]  len(ids))
        cur.execute(fSELECT id, email, username, created_at FROM users WHERE id IN ({fmt}), ids)
        _ = cur.fetchall()
    t1 = time.time()
    return t1 - t0


def mysql_cleanup(conn, batch_id str) - int
    
    Borra los usuarios insertados para el batch_id.
    Devuelve número de filas eliminadas.
    
    with conn.cursor() as cur
        cur.execute(DELETE FROM users WHERE email LIKE %s, (fbench_{batch_id}_%@example.com,))
        deleted = cur.rowcount
    conn.commit()
    return deleted


def redis_insert(r redis.Redis, batch_id str, rows List[Tuple[str, str, str]]) - Tuple[float, List[str]]
    
    Inserta N usuarios como hashes key = user{batch_id}{i}{uuid}
    Campos email, username, password_hash, created_at
    Devuelve (tiempo, [keys])
    
    keys = []
    pipe = r.pipeline()
    t0 = time.time()
    created_at = time.strftime(%Y-%m-%d %H%M%S, time.gmtime())
    for i, (email, username, password_hash) in enumerate(rows)
        k = fuser{batch_id}{i}{uuid.uuid4().hex[8]}
        keys.append(k)
        pipe.hset(k, mapping={
            email email,
            username username,
            password_hash password_hash,
            created_at created_at
        })
    pipe.execute()
    t1 = time.time()
    return (t1 - t0), keys


def redis_read(r redis.Redis, keys List[str]) - float
    
    Lee N hashes con pipeline; devuelve tiempo en segundos.
    
    pipe = r.pipeline()
    t0 = time.time()
    for k in keys
        pipe.hgetall(k)
    _ = pipe.execute()
    t1 = time.time()
    return t1 - t0


def redis_cleanup(r redis.Redis, keys List[str]) - int
    
    Borra las keys creadas. Devuelve cuántas se eliminaron.
    
    if not keys
        return 0
    return r.delete(keys)


def main()
    print(=== Benchmark Redis (hashes) vs MariaDB (users) ===)

    # Defaults según lo que proporcionaste
    default_mysql_host = 127.0.0.1
    default_mysql_port = 3306
    default_mysql_user = libros_user
    default_mysql_pass = 666
    default_mysql_db   = Libros

    default_redis_host = 127.0.0.1
    default_redis_port = 6379
    default_redis_db   = 0
    default_redis_pass =   # sin password por defecto

    # Pedir datos al usuario (con defaults)
    print(n-- Datos de MariaDB --)
    m_host = prompt_with_default(Host, default_mysql_host)
    m_port = int(prompt_with_default(Puerto, default_mysql_port))
    m_user = prompt_with_default(Usuario, default_mysql_user)
    m_pass = prompt_secret_with_default(Contraseña, default_mysql_pass)
    m_db   = prompt_with_default(Base de datos, default_mysql_db)

    print(n-- Datos de Redis --)
    r_host = prompt_with_default(Host, default_redis_host)
    r_port = int(prompt_with_default(Puerto, default_redis_port))
    r_db   = int(prompt_with_default(DB (índice), default_redis_db))
    r_pass = prompt_secret_with_default(Contraseña, default_redis_pass)

    n_records = int(prompt_with_default(nCantidad de usuarios a insertarleER (N), 500))

    # Identificador único del batch para trazabilidad y limpieza
    batch_id = uuid.uuid4().hex[10]

    # Conexiones
    try
        mysql_conn = connect_mysql(m_host, m_port, m_user, m_pass, m_db)
    except Exception as e
        print(f[ERROR] Conexión a MariaDB falló {e}, file=sys.stderr)
        sys.exit(2)

    try
        rcli = connect_redis(r_host, r_port, r_db, r_pass if r_pass else None)
        # prueba ping
        rcli.ping()
    except Exception as e
        print(f[ERROR] Conexión a Redis falló {e}, file=sys.stderr)
        mysql_conn.close()
        sys.exit(3)

    # Verificar tabla users
    try
        check_users_table(mysql_conn)
    except Exception as e
        print(f[ERROR] Verificación de tabla 'users' falló {e}, file=sys.stderr)
        mysql_conn.close()
        sys.exit(4)

    # Preparar datos
    rows = prepare_mysql_batch(mysql_conn, batch_id, n_records)

    # ----- INSERT + READ en MariaDB -----
    try
        t_ins_mysql, ids = mysql_insert(mysql_conn, rows)
        t_read_mysql = mysql_read(mysql_conn, ids)
    except Exception as e
        print(f[ERROR] Operaciones MySQL fallaron {e}, file=sys.stderr)
        # Intentar limpieza parcial
        try
            deleted = mysql_cleanup(mysql_conn, batch_id)
            print(f[LIMPIEZA] MySQL eliminados {deleted} usuarios (parcial).)
        except Exception as e2
            print(f[ERROR] Limpieza MySQL falló {e2}, file=sys.stderr)
        mysql_conn.close()
        sys.exit(5)

    # ----- INSERT + READ en Redis (hashes) -----
    try
        t_ins_redis, redis_keys = redis_insert(rcli, batch_id, rows)
        t_read_redis = redis_read(rcli, redis_keys)
    except Exception as e
        print(f[ERROR] Operaciones Redis fallaron {e}, file=sys.stderr)
        # Intentar limpieza parcial MySQL
        try
            deleted = mysql_cleanup(mysql_conn, batch_id)
            print(f[LIMPIEZA] MySQL eliminados {deleted} usuarios (parcial).)
        except Exception as e2
            print(f[ERROR] Limpieza MySQL falló {e2}, file=sys.stderr)
        mysql_conn.close()
        sys.exit(6)

    # Resultados
    print(n=== RESULTADOS (segundos) ===)
    print(fMariaDB  - Insertar {n_records} {t_ins_mysql.6f} s)
    print(fMariaDB  - Leer     {len(ids)} {t_read_mysql.6f} s)
    print(fRedis    - Insertar {n_records} {t_ins_redis.6f} s)
    print(fRedis    - Leer     {len(redis_keys)} {t_read_redis.6f} s)

    # Relación simple
    def ratio(a, b) - str
        try
            return f{ab.2f}x
        except ZeroDivisionError
            return ∞

    print(n=== COMPARATIVA (aprox) ===)
    print(fInsert Redis  Insert MariaDB {ratio(t_ins_redis, t_ins_mysql)})
    print(fLeer   Redis  Leer   MariaDB {ratio(t_read_redis, t_read_mysql)})

    # ----- LIMPIEZA -----
    print(n=== LIMPIEZA ===)
    try
        del_mysql = mysql_cleanup(mysql_conn, batch_id)
        print(fMySQL eliminados {del_mysql} usuarios del batch {batch_id}.)
    except Exception as e
        print(f[ADVERTENCIA] No se pudieron borrar usuarios en MySQL {e}, file=sys.stderr)

    try
        del_redis = redis_cleanup(rcli, redis_keys)
        print(fRedis eliminadas {del_redis} keys del batch {batch_id}.)
    except Exception as e
        print(f[ADVERTENCIA] No se pudieron borrar keys en Redis {e}, file=sys.stderr)

    # Cerrar conexiones
    mysql_conn.close()
    # rcli es un cliente sin 'close' necesario; si se usa ConnectionPool, se gestiona solo.

    print(nListo. Todo quedó limpio. ✔)


if __name__ == __main__
    try
        main()
    except KeyboardInterrupt
        print(nCancelado por el usuario., file=sys.stderr)
        sys.exit(130)

