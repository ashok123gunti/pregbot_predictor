/*
SQLyog Community v13.1.1 (64 bit)
MySQL - 5.5.29 : Database - pregbot_db
*********************************************************************
*/

/*!40101 SET NAMES utf8 */;

/*!40101 SET SQL_MODE=''*/;

/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
CREATE DATABASE /*!32312 IF NOT EXISTS*/`pregbot_db` /*!40100 DEFAULT CHARACTER SET latin1 */;

USE `pregbot_db`;

/*Table structure for table `appointments` */

DROP TABLE IF EXISTS `appointments`;

CREATE TABLE `appointments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `patient_id` int(11) DEFAULT NULL,
  `doctor_id` int(11) DEFAULT NULL,
  `appointment_type` varchar(20) DEFAULT NULL,
  `scheduled_date` date NOT NULL,
  `scheduled_time` time NOT NULL,
  `duration_minutes` int(11) DEFAULT '30',
  `reason` text,
  `symptoms_summary` text,
  `status` varchar(20) DEFAULT 'scheduled',
  `meeting_link` varchar(500) DEFAULT NULL,
  `notes` text,
  `prescription_id` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `patient_id` (`patient_id`),
  KEY `idx_doctor_date` (`doctor_id`,`scheduled_date`),
  CONSTRAINT `appointments_ibfk_1` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
  CONSTRAINT `appointments_ibfk_2` FOREIGN KEY (`doctor_id`) REFERENCES `doctors` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*Data for the table `appointments` */

/*Table structure for table `chat_history` */

DROP TABLE IF EXISTS `chat_history`;

CREATE TABLE `chat_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `user_message` text NOT NULL,
  `bot_response` text NOT NULL,
  `intent` varchar(50) DEFAULT 'general',
  `entities` text,
  `confidence` decimal(5,4) DEFAULT '0.0000',
  `session_id` varchar(100) DEFAULT NULL,
  `chat_metadata` text,
  `sentiment` varchar(20) DEFAULT 'neutral',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_intent` (`intent`),
  KEY `idx_session` (`session_id`),
  CONSTRAINT `chat_history_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=latin1;

/*Data for the table `chat_history` */


/*Table structure for table `doctor_alerts` */

DROP TABLE IF EXISTS `doctor_alerts`;

CREATE TABLE `doctor_alerts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `patient_id` int(11) DEFAULT NULL,
  `prediction_id` int(11) DEFAULT NULL,
  `alert_type` varchar(50) DEFAULT NULL,
  `priority` varchar(20) DEFAULT NULL,
  `status` enum('pending','reviewed','resolved') DEFAULT 'pending',
  `doctor_notes` text,
  `alert_metadata` text,
  `reviewed_by` int(11) DEFAULT NULL,
  `reviewed_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `metadata` text,
  PRIMARY KEY (`id`),
  KEY `patient_id` (`patient_id`),
  KEY `prediction_id` (`prediction_id`),
  KEY `reviewed_by` (`reviewed_by`),
  KEY `idx_status` (`status`),
  KEY `idx_priority` (`priority`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_alert_priority` (`priority`),
  KEY `idx_alert_created` (`created_at`),
  CONSTRAINT `doctor_alerts_ibfk_1` FOREIGN KEY (`patient_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `doctor_alerts_ibfk_2` FOREIGN KEY (`prediction_id`) REFERENCES `risk_predictions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `doctor_alerts_ibfk_3` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=latin1;

/*Data for the table `doctor_alerts` */


/*Table structure for table `doctor_recommendations` */

DROP TABLE IF EXISTS `doctor_recommendations`;

CREATE TABLE `doctor_recommendations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `patient_id` int(11) DEFAULT NULL,
  `doctor_id` int(11) DEFAULT NULL,
  `recommendation_type` varchar(20) DEFAULT NULL,
  `title` varchar(200) DEFAULT NULL,
  `description` text,
  `prescription_details` text,
  `tests_requested` text,
  `referral_to` varchar(200) DEFAULT NULL,
  `priority` varchar(20) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'pending',
  `follow_up_date` date DEFAULT NULL,
  `follow_up_notes` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `doctor_id` (`doctor_id`),
  KEY `idx_patient_status` (`patient_id`,`status`),
  CONSTRAINT `doctor_recommendations_ibfk_1` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
  CONSTRAINT `doctor_recommendations_ibfk_2` FOREIGN KEY (`doctor_id`) REFERENCES `doctors` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*Data for the table `doctor_recommendations` */

/*Table structure for table `doctors` */

DROP TABLE IF EXISTS `doctors`;

CREATE TABLE `doctors` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `medical_license` varchar(100) DEFAULT NULL,
  `specialization` varchar(150) DEFAULT NULL,
  `qualifications` text,
  `years_experience` int(11) DEFAULT NULL,
  `hospital_affiliation` varchar(200) DEFAULT NULL,
  `clinic_address` text,
  `consultation_fee` decimal(10,2) DEFAULT NULL,
  `available_days` varchar(100) DEFAULT NULL,
  `available_hours` varchar(100) DEFAULT NULL,
  `teleconsultation_available` tinyint(1) DEFAULT '0',
  `ratings` decimal(3,2) DEFAULT '0.00',
  `total_reviews` int(11) DEFAULT '0',
  `biography` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user` (`user_id`),
  UNIQUE KEY `unique_license` (`medical_license`),
  KEY `idx_specialization` (`specialization`),
  CONSTRAINT `doctors_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*Data for the table `doctors` */

/*Table structure for table `educational_content` */

DROP TABLE IF EXISTS `educational_content`;

CREATE TABLE `educational_content` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `content_type` varchar(20) DEFAULT NULL,
  `trimester_applicable` varchar(50) DEFAULT NULL,
  `category` varchar(100) DEFAULT NULL,
  `content` text,
  `video_url` varchar(500) DEFAULT NULL,
  `image_url` varchar(500) DEFAULT NULL,
  `doctor_approved` tinyint(1) DEFAULT '0',
  `view_count` int(11) DEFAULT '0',
  `like_count` int(11) DEFAULT '0',
  `created_by` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*Data for the table `educational_content` */

/*Table structure for table `mental_health_log` */

DROP TABLE IF EXISTS `mental_health_log`;

CREATE TABLE `mental_health_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `patient_id` int(11) DEFAULT NULL,
  `mood` varchar(50) DEFAULT NULL,
  `stress_level` int(11) DEFAULT NULL,
  `anxiety_level` int(11) DEFAULT NULL,
  `sleep_hours` decimal(3,1) DEFAULT NULL,
  `notes` text,
  `sentiment` varchar(20) DEFAULT NULL,
  `recommendation` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_patient_id` (`patient_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_sentiment` (`sentiment`),
  CONSTRAINT `mental_health_log_ibfk_1` FOREIGN KEY (`patient_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=latin1;

/*Data for the table `mental_health_log` */


/*Table structure for table `mental_health_logs` */

DROP TABLE IF EXISTS `mental_health_logs`;

CREATE TABLE `mental_health_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `patient_id` int(11) DEFAULT NULL,
  `log_date` date NOT NULL,
  `mood` varchar(20) DEFAULT NULL,
  `stress_level` int(11) DEFAULT NULL,
  `sleep_hours` decimal(3,1) DEFAULT NULL,
  `sleep_quality` varchar(20) DEFAULT NULL,
  `exercise_minutes` int(11) DEFAULT NULL,
  `relaxation_minutes` int(11) DEFAULT NULL,
  `social_interaction_hours` decimal(3,1) DEFAULT NULL,
  `notes` text,
  `ai_sentiment_analysis` text,
  `recommendations` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_patient_date` (`patient_id`,`log_date`),
  CONSTRAINT `mental_health_logs_ibfk_1` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*Data for the table `mental_health_logs` */

/*Table structure for table `notifications` */

DROP TABLE IF EXISTS `notifications`;

CREATE TABLE `notifications` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `notification_type` varchar(20) DEFAULT NULL,
  `title` varchar(200) NOT NULL,
  `message` text NOT NULL,
  `priority` varchar(20) DEFAULT 'medium',
  `is_read` tinyint(1) DEFAULT '0',
  `action_url` varchar(500) DEFAULT NULL,
  `related_id` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user_read` (`user_id`,`is_read`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*Data for the table `notifications` */

/*Table structure for table `nutrition_logs` */

DROP TABLE IF EXISTS `nutrition_logs`;

CREATE TABLE `nutrition_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `patient_id` int(11) DEFAULT NULL,
  `log_date` date NOT NULL,
  `meal_type` varchar(20) DEFAULT NULL,
  `food_items` text,
  `calories` int(11) DEFAULT NULL,
  `protein_g` int(11) DEFAULT NULL,
  `carbs_g` int(11) DEFAULT NULL,
  `fat_g` int(11) DEFAULT NULL,
  `water_intake_ml` int(11) DEFAULT NULL,
  `supplements_taken` text,
  `notes` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_patient_date` (`patient_id`,`log_date`),
  CONSTRAINT `nutrition_logs_ibfk_1` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*Data for the table `nutrition_logs` */

/*Table structure for table `patient_profiles` */

DROP TABLE IF EXISTS `patient_profiles`;

CREATE TABLE `patient_profiles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `age` int(11) DEFAULT NULL,
  `trimester` int(11) DEFAULT NULL,
  `blood_pressure_category` varchar(20) DEFAULT NULL,
  `weight` decimal(5,2) DEFAULT NULL,
  `height` decimal(5,2) DEFAULT NULL,
  `medical_history` text,
  `allergies` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_trimester` (`trimester`),
  CONSTRAINT `patient_profiles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;

/*Data for the table `patient_profiles` */


/*Table structure for table `patients` */

DROP TABLE IF EXISTS `patients`;

CREATE TABLE `patients` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `date_of_birth` date DEFAULT NULL,
  `blood_group` varchar(10) DEFAULT NULL,
  `height_cm` decimal(5,2) DEFAULT NULL,
  `weight_kg` decimal(5,2) DEFAULT NULL,
  `pre_pregnancy_bmi` decimal(4,2) DEFAULT NULL,
  `last_menstrual_date` date DEFAULT NULL,
  `expected_due_date` date DEFAULT NULL,
  `current_trimester` int(11) DEFAULT '1',
  `current_week` int(11) DEFAULT NULL,
  `parity` int(11) DEFAULT '0',
  `gravida` int(11) DEFAULT '1',
  `medical_history` text,
  `surgical_history` text,
  `drug_allergies` text,
  `current_medications` text,
  `family_history` text,
  `lifestyle_factors` text,
  `emergency_contact_name` varchar(100) DEFAULT NULL,
  `emergency_contact_phone` varchar(20) DEFAULT NULL,
  `preferred_hospital` varchar(200) DEFAULT NULL,
  `insurance_info` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user` (`user_id`),
  KEY `idx_due_date` (`expected_due_date`),
  KEY `idx_trimester` (`current_trimester`),
  CONSTRAINT `patients_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*Data for the table `patients` */

/*Table structure for table `recommendations` */

DROP TABLE IF EXISTS `recommendations`;

CREATE TABLE `recommendations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `trimester` int(11) DEFAULT NULL,
  `category` varchar(50) DEFAULT NULL,
  `title` varchar(200) DEFAULT NULL,
  `description` text,
  `for_condition` varchar(100) DEFAULT NULL,
  `created_by` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `created_by` (`created_by`),
  KEY `idx_trimester` (`trimester`),
  KEY `idx_category` (`category`),
  CONSTRAINT `recommendations_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=latin1;

/*Data for the table `recommendations` */


/*Table structure for table `risk_predictions` */

DROP TABLE IF EXISTS `risk_predictions`;

CREATE TABLE `risk_predictions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `patient_id` int(11) DEFAULT NULL,
  `prediction` varchar(20) DEFAULT NULL,
  `confidence` decimal(5,4) DEFAULT NULL,
  `factors_age` int(11) DEFAULT NULL,
  `factors_trimester` int(11) DEFAULT NULL,
  `factors_bp_category` varchar(20) DEFAULT NULL,
  `factors_symptom_severity` varchar(20) DEFAULT NULL,
  `factors_symptom_name` varchar(100) DEFAULT NULL,
  `explanation` text,
  `is_emergency` tinyint(1) DEFAULT '0',
  `doctor_reviewed` tinyint(1) DEFAULT '0',
  `doctor_feedback` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_patient_id` (`patient_id`),
  KEY `idx_prediction` (`prediction`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_risk_emergency` (`is_emergency`),
  KEY `idx_risk_created` (`created_at`),
  CONSTRAINT `risk_predictions_ibfk_1` FOREIGN KEY (`patient_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=latin1;

/*Data for the table `risk_predictions` */


/*Table structure for table `sessions` */

DROP TABLE IF EXISTS `sessions`;

CREATE TABLE `sessions` (
  `id` varchar(128) NOT NULL,
  `data` blob,
  `expiry` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_expiry` (`expiry`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

/*Data for the table `sessions` */

/*Table structure for table `symptoms_log` */

DROP TABLE IF EXISTS `symptoms_log`;

CREATE TABLE `symptoms_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `patient_id` int(11) DEFAULT NULL,
  `symptom_name` varchar(100) DEFAULT NULL,
  `severity` varchar(20) DEFAULT NULL,
  `duration_days` int(11) DEFAULT NULL,
  `description` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_patient_id` (`patient_id`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `symptoms_log_ibfk_1` FOREIGN KEY (`patient_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=latin1;

/*Data for the table `symptoms_log` */


/*Table structure for table `users` */

DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `full_name` varchar(100) NOT NULL,
  `user_type` enum('patient','doctor') NOT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_email` (`email`),
  KEY `idx_user_type` (`user_type`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=latin1;

/*Data for the table `users` */

insert  into `users`(`id`,`email`,`password`,`full_name`,`user_type`,`phone`,`created_at`) values 
(1,'aravind@gmail.com','pbkdf2:sha256:260000$SxEWM01TvaR0Rhrj$478e38adb946bfd95565d7385159d989c80bccebc9cf3dce6e1d960e68dae56e','aravind','patient','9898767875','2025-12-07 15:12:03'),
(2,'admin@gmail.com','pbkdf2:sha256:260000$RCAM80Fc9ZHZ7Ji3$a16e790982d73af090dcd065cff739b538d19ca40c245c7c739c4b52825387f0','System Admin','doctor','+1234567890','2025-12-07 15:20:27'),

