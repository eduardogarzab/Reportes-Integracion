/*M!999999\- enable the sandbox mode */
-- MariaDB dump 10.19  Distrib 10.5.27-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: Libros
-- ------------------------------------------------------
-- Server version	10.5.27-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `authors`
--

DROP TABLE IF EXISTS `authors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `authors` (
  `author_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`author_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `authors`
--

LOCK TABLES `authors` WRITE;
/*!40000 ALTER TABLE `authors` DISABLE KEYS */;
INSERT INTO `authors` VALUES (6,'Aldous Huxley'),(11,'Antoine de Saint-Exupéry'),(3,'Cormac McCarthy'),(8,'F. Scott Fitzgerald'),(12,'Frank Herbert'),(10,'Fyodor Dostoevsky'),(7,'George Orwell'),(2,'Harper Lee'),(4,'Herman Melville'),(1,'Homer'),(20,'J.R.R. Tolkien'),(17,'Jack Kerouac'),(5,'Jane Austen'),(16,'Jon Krakauer'),(9,'Khaled Hosseini'),(13,'Marcus Aurelius'),(19,'Mary Shelley'),(18,'Miguel de Cervantes'),(15,'Plato'),(14,'Ray Bradbury');
/*!40000 ALTER TABLE `authors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `book_authors`
--

DROP TABLE IF EXISTS `book_authors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `book_authors` (
  `isbn` varchar(20) NOT NULL,
  `author_id` int(11) NOT NULL,
  PRIMARY KEY (`isbn`,`author_id`),
  KEY `fk_ba_authors` (`author_id`),
  CONSTRAINT `fk_ba_authors` FOREIGN KEY (`author_id`) REFERENCES `authors` (`author_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_ba_books` FOREIGN KEY (`isbn`) REFERENCES `books` (`isbn`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `book_authors`
--

LOCK TABLES `book_authors` WRITE;
/*!40000 ALTER TABLE `book_authors` DISABLE KEYS */;
INSERT INTO `book_authors` VALUES ('977-0553380163',2),('977-0553380163',15),('978-0060850524',6),('978-0060850525',14),('978-0061120084',2),('978-0140449136',1),('978-0140449181',13),('978-0140449198',15),('978-0140449266',1),('978-0141187761',17),('978-0142437209',19),('978-0156012195',11),('978-0307387899',9),('978-0385486804',16),('978-0553213119',5),('978-0553380163',12),('978-0743273565',8);
/*!40000 ALTER TABLE `book_authors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `books`
--

DROP TABLE IF EXISTS `books`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `books` (
  `isbn` varchar(20) NOT NULL,
  `title` varchar(255) NOT NULL,
  `year` int(11) DEFAULT NULL,
  `price` decimal(10,2) NOT NULL,
  `stock` int(11) NOT NULL DEFAULT 0,
  `genre_id` int(11) NOT NULL,
  `format_id` int(11) NOT NULL,
  PRIMARY KEY (`isbn`),
  KEY `fk_books_genres` (`genre_id`),
  KEY `fk_books_formats` (`format_id`),
  CONSTRAINT `fk_books_formats` FOREIGN KEY (`format_id`) REFERENCES `formats` (`format_id`),
  CONSTRAINT `fk_books_genres` FOREIGN KEY (`genre_id`) REFERENCES `genres` (`genre_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `books`
--

LOCK TABLES `books` WRITE;
/*!40000 ALTER TABLE `books` DISABLE KEYS */;
INSERT INTO `books` VALUES ('977-0553380163','Aguas Parte 2',2025,11.12,5,2,1),('978-0060850524','Nuevo Mundo',2006,15.15,15,6,1),('978-0060850525','Fahrenheit 451',2012,8.40,19,6,2),('978-0061120084','To Kill a Mockingbird',2006,10.99,40,2,1),('978-0140449136','The Odyssey',1999,12.50,25,1,1),('978-0140449181','Meditations',2002,10.99,32,11,1),('978-0140449198','The Republic',2003,9.99,20,11,1),('978-0140449266','The Iliad',2003,12.00,28,1,2),('978-0141187761','On the Road',2000,11.00,23,13,1),('978-0142437209','Frankenstein',2004,9.00,38,15,1),('978-0156012195','The Little Prince',2000,9.50,45,9,1),('978-0307387899','The Kite Runner',2007,13.75,15,7,2),('978-0385486804','Into the Wild',1997,13.20,14,12,2),('978-0553213119','Pride and Prejudice',2003,8.99,50,5,2),('978-0553380163','Dune',1990,15.99,27,10,2),('978-0743273565','The Great Gatsby',2004,10.25,22,2,1);
/*!40000 ALTER TABLE `books` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `formats`
--

DROP TABLE IF EXISTS `formats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `formats` (
  `format_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`format_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `formats`
--

LOCK TABLES `formats` WRITE;
/*!40000 ALTER TABLE `formats` DISABLE KEYS */;
INSERT INTO `formats` VALUES (2,'Digital'),(1,'Físico'),(3,'Sencillito');
/*!40000 ALTER TABLE `formats` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `genres`
--

DROP TABLE IF EXISTS `genres`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `genres` (
  `genre_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`genre_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `genres`
--

LOCK TABLES `genres` WRITE;
/*!40000 ALTER TABLE `genres` DISABLE KEYS */;
INSERT INTO `genres` VALUES (4,'Adventure'),(13,'Beat Literature'),(12,'Biography'),(9,'Children'),(14,'Classic'),(7,'Drama'),(6,'Dystopian'),(1,'Epic'),(2,'Fiction'),(15,'Horror'),(11,'Philosophy'),(3,'Post-apocalyptic'),(8,'Psychological Fiction'),(5,'Romance'),(10,'Science Fiction');
/*!40000 ALTER TABLE `genres` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `items`
--

DROP TABLE IF EXISTS `items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `items_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `items`
--

LOCK TABLES `items` WRITE;
/*!40000 ALTER TABLE `items` DISABLE KEYS */;
INSERT INTO `items` VALUES (1,1,'Segundo libro de prueba','2025-09-15 20:12:52');
/*!40000 ALTER TABLE `items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `refresh_tokens`
--

DROP TABLE IF EXISTS `refresh_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `refresh_tokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `token` varchar(500) NOT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `refresh_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=46 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `refresh_tokens`
--

LOCK TABLES `refresh_tokens` WRITE;
/*!40000 ALTER TABLE `refresh_tokens` DISABLE KEYS */;
INSERT INTO `refresh_tokens` VALUES (1,1,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3NTg1NzE0MDV9.UGPLmcjOzS9RiknDcUyXdqCaEPOcGJ58WfprRwxTnBc','2025-09-22 20:03:25','2025-09-15 20:03:25'),(2,1,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3NTg1NzE4NjV9.v9-NYlhl6odZRFls2lnE8WBOeaXN6xvzgIVVtD1GPXw','2025-09-22 20:11:05','2025-09-15 20:11:05'),(3,1,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3NTg1NzE5MzJ9.hcg3haJs36jweJp-tvzjiXfqmx3CzCs6Zs8IwrW7pi8','2025-09-22 20:12:12','2025-09-15 20:12:12'),(4,6,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo2LCJleHAiOjE3NTg2NTg5MTN9.xJQ0DHi4TV1glvc5W6ocUVxNhawFhBpOF2jaWA0VGm8','2025-09-23 20:21:53','2025-09-16 20:21:53'),(5,6,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo2LCJleHAiOjE3NTg2NTkwNDR9.3_Hr29ZXUvLPn1tDYZSlxxHKK7qv7rJ8Hk_vGawOgeo','2025-09-23 20:24:04','2025-09-16 20:24:04'),(6,6,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo2LCJleHAiOjE3NTg2NTk0NDB9.QMP9JogxCWnVpZRWYZCZRS2F3ZoNILPKEIdVHq5fpWE','2025-09-23 20:30:40','2025-09-16 20:30:40'),(7,7,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo3LCJleHAiOjE3NTkxNzQzMTR9.HZ-8RMecNjjJXqW9Az7sD_Xntpsb51kanaAH6xzwHhI','2025-09-29 19:31:54','2025-09-22 19:31:54'),(8,7,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo3LCJleHAiOjE3NTkxNzQzNTh9.fon5xqq3R5E2juWzGK8-ZhStX47skVyF5MR7bJDRlm0','2025-09-29 19:32:38','2025-09-22 19:32:38'),(9,7,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo3LCJleHAiOjE3NTkxNzQ3OTh9.x2PuXwfPNSvALbwuZrh_TdJPPOWkJLzPlbbVSlpkZEo','2025-09-29 19:39:58','2025-09-22 19:39:58'),(10,8,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo4LCJleHAiOjE3NTkxNzY4MzR9.srFsrYW7iqEvGvNOD3RyRpOySbxeT9oy7EgRHYDYCKQ','2025-09-29 20:13:54','2025-09-22 20:13:54'),(11,8,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo4LCJleHAiOjE3NTkxNzY5Nzl9.pLI9XQDrY_amH-2N-3JZ9AiyX1Jk6eQb7sZfeOR6zq0','2025-09-29 20:16:19','2025-09-22 20:16:19'),(12,27,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDU4OTkyNCwianRpIjoiYWJkYjU4ZWEtZTJlMS00MzBiLWEwN2MtYTEzNjc0M2E1MDExIiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIyNyIsIm5iZiI6MTc2MDU4OTkyNCwiY3NyZiI6Ijc2ZjhlNDUxLTFiZjQtNGIzYi1hZDQzLWQyZWY2MjhhMWJjNiIsImV4cCI6MTc2MTE5NDcyNH0.IK37DuzMRa2oMhnrj4igcqwSdx9YO3TiS8K7zUNGkPk','2025-10-23 04:45:24','2025-10-16 04:45:24'),(13,27,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDU5MTAyNCwianRpIjoiODI0NjUzYWMtZWNjYS00MDU5LTkzYTEtNmY2M2NmZDgxMTcwIiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIyNyIsIm5iZiI6MTc2MDU5MTAyNCwiY3NyZiI6IjNkNjdlZDY5LTZkZDUtNDNkMC1hYzQ3LTRjNjhiZjdmNDFkMiIsImV4cCI6MTc2MTE5NTgyNH0.Ok9hBgpS6cf4bPoQn54QFZcLsrySDbTIpHp36dme-oQ','2025-10-23 05:03:44','2025-10-16 05:03:44'),(14,27,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDU5MTAzNywianRpIjoiYmEzMTkwYWQtZjBkZC00MGQ3LTk5MmUtNzFlY2ZjZDJmZDA1IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIyNyIsIm5iZiI6MTc2MDU5MTAzNywiY3NyZiI6IjQ2ODg5MTgwLTJkZGUtNDcxNi04YTRiLTk4OTE4YmMwNjIyZCIsImV4cCI6MTc2MTE5NTgzN30.nIa3qMWVEIZZTAoN5iiovRijjp6m8iqRLJ1IZ70A86I','2025-10-23 05:03:57','2025-10-16 05:03:57'),(15,27,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDU5MTA0NiwianRpIjoiODk5ZjhlMmYtNmFiMi00NDkyLTgxNzItMzQyZmYzOWFkOTQ3IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIyNyIsIm5iZiI6MTc2MDU5MTA0NiwiY3NyZiI6ImJiYjc5YmI4LWQ2MGMtNDE0MC1iMjUzLWE3N2RhOTNiNTU0MCIsImV4cCI6MTc2MTE5NTg0Nn0.N2Z8haB088ENm0-Z4J0ujAfUuT28H-Z_B1PwSoBhm-w','2025-10-23 05:04:06','2025-10-16 05:04:06'),(16,27,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDU5MTA1MCwianRpIjoiMjc4OWQ4ZDItY2U1Mi00MzNjLTkxNzctZDQzN2ZkMzRhZjk0IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIyNyIsIm5iZiI6MTc2MDU5MTA1MCwiY3NyZiI6IjJmNGFkMGFkLTEzMjgtNDUzNy1hN2I0LWE2ZGMwYmI2MThiZCIsImV4cCI6MTc2MTE5NTg1MH0.6Sqs4WOb_aXGr22EWlHlD_YcGAz9wL4OVipFns5Xthg','2025-10-23 05:04:10','2025-10-16 05:04:10'),(17,27,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDU5MTgxMiwianRpIjoiZmU3MGYyZTUtZDc3YS00ODA4LWJmMjItNWM2YWFhZDExNmY0IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIyNyIsIm5iZiI6MTc2MDU5MTgxMiwiY3NyZiI6IjEwZGYxNjE3LWQwNjctNDM0ZC05YWY5LTIzZTU0MzZlZTdiNiIsImV4cCI6MTc2MTE5NjYxMn0.er7VknlpLZGmV4WbM2L7mzjPspwetFeDAXWybEm4BPs','2025-10-23 05:16:52','2025-10-16 05:16:52'),(18,27,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDU5MjIzMiwianRpIjoiYTZlNGU5MTEtYTEyMS00MmIyLTk4NDctYWIxMDRiOGY4OTA4IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIyNyIsIm5iZiI6MTc2MDU5MjIzMiwiY3NyZiI6IjA1YWIyOTEyLWVmMDItNDhkOC05M2NhLWQzMzRlODM4MGFlZSIsImV4cCI6MTc2MTE5NzAzMn0.zPx_ma3gSVuTUNZYXwSua8ye5NFyegEQ10MpuEMrl3Y','2025-10-23 05:23:52','2025-10-16 05:23:52'),(19,28,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDU5NDEzMiwianRpIjoiNmNmY2QzODktZmE5My00NWJmLWI0OTYtMGZkOTZkNzA3NTczIiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIyOCIsIm5iZiI6MTc2MDU5NDEzMiwiY3NyZiI6ImFmODVhYTc2LTkwNDMtNGE0NS05MTQ4LTg1YTM1NzlmZTllZCIsImV4cCI6MTc2MTE5ODkzMn0.hl4JV-O49F6b1fPyMa76LLUKBLovAAgUar5CjMAsYYQ','2025-10-23 05:55:32','2025-10-16 05:55:32'),(20,29,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDU5OTU4MiwianRpIjoiMjM1YjMwN2UtMGNhNC00YjgzLTkxYjUtNjlhODAyZmMzYjA2IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIyOSIsIm5iZiI6MTc2MDU5OTU4MiwiY3NyZiI6ImVmNTFkNjM4LTBkY2MtNGE4Ny1hODI4LTg1OTg4NWI5N2U4OCIsImV4cCI6MTc2MTIwNDM4Mn0.bhG5foMeWqzj9puhwpw7NxOABV43lx3Yaq3YA6bGOac','2025-10-23 07:26:22','2025-10-16 07:26:22'),(33,38,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDYwMjQ3OCwianRpIjoiY2M4MWRhMTUtZjRkOS00ODU1LTkwMzItZTk1ZGFlOGE2YTc0IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIzOCIsIm5iZiI6MTc2MDYwMjQ3OCwiY3NyZiI6ImM0ZDYyNGMxLTg5ZWUtNGIxZi04MzYzLTgzNjM2OTdiNjRjNyIsImV4cCI6MTc2MTIwNzI3OH0.1ZMmxOBiXbBo1CnHt9ts_GEMmBcsq4LJDT-W7vQAiDc','2025-10-23 08:14:38','2025-10-16 08:14:38'),(34,34,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDYwMjQ4OSwianRpIjoiNTVlMDgxMzUtOTIzMS00Y2YwLWE4OGItNTYzNjY5ZTY4NDg0IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIzNCIsIm5iZiI6MTc2MDYwMjQ4OSwiY3NyZiI6IjExZDM3ZWQ1LTc1MmYtNDA1YS04ZTgzLWJmNWRlOWYyZTc4YSIsImV4cCI6MTc2MTIwNzI4OX0.9T_FKktNEkICoABTeufCh4WOHB_NkbAW7SR68WnGAaU','2025-10-23 08:14:49','2025-10-16 08:14:49'),(36,35,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDYwMjUwNSwianRpIjoiMjEwM2U4MjgtMmNmOC00MmZkLWIyNGMtOTVhYzJhNDgxMjViIiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIzNSIsIm5iZiI6MTc2MDYwMjUwNSwiY3NyZiI6ImRmZjBjYzg2LTZlMTctNGUyOS05OGNmLTNiZGJhZmMyYzU0YiIsImV4cCI6MTc2MTIwNzMwNX0.sXEwvbMOMWQ6bFHMeBNNndd1iGXC_ASzybD3QC6JRpU','2025-10-23 08:15:05','2025-10-16 08:15:05'),(39,37,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDYwMjU2NSwianRpIjoiMjExZjlmZGItNzE0NS00OTY5LTlhNTAtNGJiNjRlZTgzOThjIiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIzNyIsIm5iZiI6MTc2MDYwMjU2NSwiY3NyZiI6IjllMmUzNzRkLTNmZDMtNDIwYi05MWQzLWQyMWMyZTJjYzA0NCIsImV4cCI6MTc2MTIwNzM2NX0.w30iF4W6ex7GcBY5rZiUK3CAztLQIJk5N-Q_NE-mnY8','2025-10-23 08:16:05','2025-10-16 08:16:05'),(40,36,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDYwMjU3MywianRpIjoiZjAzY2E2YmItZDc3Ni00ZTc4LWI3NDctNTFjYjg2NWU0ZmRhIiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIzNiIsIm5iZiI6MTc2MDYwMjU3MywiY3NyZiI6Ijk5YjM1MmQ1LTQzZDgtNGQ2Ny1hNzYzLWY2N2RjZTM0YzQyYSIsImV4cCI6MTc2MTIwNzM3M30.jkvS6-prrs_d5uBprMYiP43vpkPVYw8oshJx8t79JQs','2025-10-23 08:16:13','2025-10-16 08:16:13'),(41,1,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDYwMzUzNSwianRpIjoiZjcwMmJhMjQtOTM5YS00ZWFjLTkyYmUtNTE0ZjkyZWM1MTNjIiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIxIiwibmJmIjoxNzYwNjAzNTM1LCJjc3JmIjoiZTQ2MzA2MWEtMmE2OS00ZWQ0LThhNWUtODg4NjAwZjY5ZmEwIiwiZXhwIjoxNzYxMjA4MzM1fQ.mengJgJb6XMsKB3oErmCA8vT4XO6DDaLfB8uyD1X6sI','2025-10-23 08:32:15','2025-10-16 08:32:15'),(44,41,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDYzNzUwOCwianRpIjoiMGQzOWE4ZDUtZmVkZC00N2ZhLTllMWItMjc4NTk2MzVjMGZjIiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiI0MSIsIm5iZiI6MTc2MDYzNzUwOCwiY3NyZiI6IjM2ZDNkODBiLTc0N2ItNGM1MS04Y2RhLTU4MzJhMzc5ZGY0MiIsImV4cCI6MTc2MTI0MjMwOH0.QJmpJkomgkWXJ9KDPqTQrVNndRyXIrpMBw4m3Kv6mHw','2025-10-23 17:58:28','2025-10-16 17:58:28'),(45,42,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MDYzODYzMCwianRpIjoiMDFjZDk4ODItOWY2MC00NjllLWE4NGUtZTg0MjczNWM0NTY5IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiJKb3JnZVNlcmFuZ2VsbGkxMSIsIm5iZiI6MTc2MDYzODYzMCwiY3NyZiI6IjM4NWQ2YzYwLWIzNTMtNGU1ZC1iNGJhLTZlNzRjYWMyMzc4NiIsImV4cCI6MTc2MTI0MzQzMH0.WFQrtmPyGeoCOc1YcuZyjeP_9RUuVcSG7QcBX-5b3KU','2025-10-23 18:17:10','2025-10-16 18:17:10');
/*!40000 ALTER TABLE `refresh_tokens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=43 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'jorge','jorge@example.com','$2b$12$2rbore8PIbZSzRRWwJFHh.owIqK1qY9YfD9d13oDNGxqAGPYLSAvS','2025-09-15 19:50:18','2025-09-15 19:50:18'),(2,'Usuario de Prueba','test@user.com','$2b$12$e9K4d6WzTffGqhBRkctZUecdadWfkLd89KwrQXaKDPaRBtszoGvh6','2025-09-16 19:57:06','2025-09-16 19:57:06'),(5,'JorgeSeran','jorge@user.com','$2b$12$X8/sYE.gbxUHa7DpEsbLke9bv5xCpdWgmJHWAwfPBMhnIaPKsqN9O','2025-09-16 20:17:18','2025-09-16 20:17:18'),(6,'JorgeSerangelli','j@user.com','$2b$12$cm7jAfNGYnGuvib0LD67NOjKOAUvIY3Wijhn9ru9KWcTjKhXz5F.O','2025-09-16 20:21:28','2025-09-16 20:21:28'),(7,'usuario_prueba','usuario@ejemplo.com','$2b$12$eKgzTA4OU4FjfIJt5lkl7evyoMFz6QEzB5Mpd70ZIwSxT/1Mj.h8a','2025-09-22 19:27:19','2025-09-22 19:27:19'),(8,'Jorge Enrique Serangelli Andrade','j@seran.com','$2b$12$JWAJw2/lSMqo66d1yyQerOk0I9jtWNwF4W2upRsWbxXi5mhgOrRu2','2025-09-22 20:13:11','2025-09-22 20:13:11'),(18,'user4038','user4038@test.com','$2b$12$uZ75POmDn78M2BbQrZwJ4uI/6Odm8vWaxLmk2./Cp.zyUHc6ESpG2','2025-10-09 20:22:27','2025-10-09 20:22:27'),(19,'user1594','user1594@test.com','$2b$12$S1cd1qhXqiB1cIfanfqDGuQerdOJxPlx2TlMYsCCUJsYJg3Omyype','2025-10-09 20:22:28','2025-10-09 20:22:28'),(20,'user2135','user2135@test.com','$2b$12$fTDf0ZGf1IBZAdYWqIFtOuxKg/..R2bVVLocfm4CX8Ij3gXktviG2','2025-10-09 20:22:29','2025-10-09 20:22:29'),(21,'user793','user793@test.com','$2b$12$uqKB8914R7YOwFcLq4qahOS15dY28nFruHjs0M3V1F7YrpKj.T.H6','2025-10-09 20:22:30','2025-10-09 20:22:30'),(22,'user577','user577@test.com','$2b$12$lTnLl3uswBvrt7JAwBgNZ.iha3xVnIheT1OkCIbCpMdDD3YS7K.Ou','2025-10-09 20:22:31','2025-10-09 20:22:31'),(23,'user5475','user5475@test.com','$2b$12$2CnKzEZ..LN54eBgRP5vNeRqrUzzpnJnPdLQaOAMjSBIjikn4vFDu','2025-10-09 20:22:32','2025-10-09 20:22:32'),(24,'user9858','user9858@test.com','$2b$12$Ac/dx/Sk34bTwR5TtRUKeeA3J99sayC3rhs3BOZu5A1aawkZbYrHG','2025-10-09 20:22:33','2025-10-09 20:22:33'),(25,'user2864','user2864@test.com','$2b$12$Qe1teVX4yDtJeAie82hCVeIT20ohcH8JXlit6g5YHZ5BfKvrpuqEC','2025-10-09 20:22:34','2025-10-09 20:22:34'),(26,'jorge_test','jorge@example3.com','$2b$12$3uSc36DXlG5gcx12X2qHUug8nmH5.qz6Os9ID0IkOk9hIfpU9m1Fy','2025-10-13 20:14:23','2025-10-13 20:14:23'),(27,'Sencillito','jorge.serangelli@udem.edu','$2b$12$6i4joco0buSiLrg5EXTkcOibL2xBG9He/gYBWQaT9J4KmdcrJeaBe','2025-10-16 04:33:38','2025-10-16 04:33:38'),(28,'Seran1234','jer@gmail.com','$2b$12$gJpyvN6xe.pG8B.je1JEouWUE9rNTTni2HUr7SM8z4pWMNmCRY2R6','2025-10-16 05:55:10','2025-10-16 05:55:10'),(29,'JavaUsuario','andrade@gmail.com','$2b$12$UG7bfb5fD9JQiMlosuXKiOa6HeXl1hpmBR2kQFGKvHts7CsBpTGnW','2025-10-16 07:26:03','2025-10-16 07:26:03'),(33,'user1730','user1730@test.com','$2b$12$MA8zxfyodcjoBe4QvOhmpu8BvkH.xYU3DNzgoRuVJLhmy2LZbOEbq','2025-10-16 08:04:58','2025-10-16 08:04:58'),(34,'user967','user967@test.com','$2b$12$91eSHRtwaGqH1TxV5Viaa.4drY9sFa1H9UNtGB/GWRqRtn5MfOeb.','2025-10-16 08:12:23','2025-10-16 08:12:23'),(35,'user4354','user4354@test.com','$2b$12$fJiNIes5RyI/sEzVy58KS.GIjJtjBb0OwZNcfVkk.03Xsh4vMcpuu','2025-10-16 08:12:23','2025-10-16 08:12:23'),(36,'user6077','user6077@test.com','$2b$12$SaubMHmFObRQQv4YSD1C.uEcr1sjf29LxW3F6sCoIWRes5GEmX5q6','2025-10-16 08:12:23','2025-10-16 08:12:23'),(37,'user9740','user9740@test.com','$2b$12$04gFMZ2JMWpjVOdG6PQkceWM8Tr62/HALz9hHoRrmUDZykoS6wg7K','2025-10-16 08:12:23','2025-10-16 08:12:23'),(38,'user384','user384@test.com','$2b$12$kFID7RGO1jlPcFh.pwvJ9uqQhecalPV8rvFkDXwNmHd6HIs9S0x7O','2025-10-16 08:12:23','2025-10-16 08:12:23'),(39,'ma','holin@ejemplo.com','$2b$12$OkaBuTwZaM4FrsRQ9RA41uw/iDP1.bQjCFLWwCOhSjQ74Gf36Hsr6','2025-10-16 08:33:25','2025-10-16 08:33:25'),(40,'Eljuanito','juancito@udem.edu','$2b$12$xV98Zo9UmMRJpuhcvBymTufPiu8Su7bKc4LETjQtA0bSyw7GyOQRS','2025-10-16 16:59:55','2025-10-16 16:59:55'),(41,'juanito2','o@gmail.com','$2b$12$32BfU.V5kidZGQ2xkW0HVeOVcGuv.L6kcyc65jHRRl9pXBEjw2nCq','2025-10-16 17:08:17','2025-10-16 17:08:17'),(42,'JorgeSerangelli11','jorl@gmail.com','$2b$12$5nT25TbrZOXe6fTr0Q95auDYf2IYcwu08vghNvAGRukyfAxVS7d3W','2025-10-16 18:16:53','2025-10-16 18:16:53');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-10-16 18:48:42
