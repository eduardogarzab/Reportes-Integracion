-- Script de creación para la tabla 'images' en MariaDB

-- Asegúrate de estar usando la base de datos correcta
-- USE tu_base_de_datos;

CREATE TABLE IF NOT EXISTS images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_archivo VARCHAR(255) NOT NULL,
    fecha_subida DATETIME NOT NULL,
    tamaño_archivo BIGINT NOT NULL,
    tipo_mime VARCHAR(100),
    url_firmada VARCHAR(1024), -- Almacenamos la URL generada al subir
    
    -- Un índice en el nombre del archivo puede ser útil
    INDEX idx_nombre_archivo (nombre_archivo)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;