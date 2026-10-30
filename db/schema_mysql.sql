-- 表情符号课堂情绪检查器系统 MySQL 8 建表脚本
-- 由 SQLAlchemy 模型生成，字段、索引与约束与 backend/app/models 保持一致。
-- 开发与演示默认使用 SQLite（AUTO_CREATE_TABLES=true 时自动建表）；
-- 本脚本用于可选部署形态，未在 MySQL 上完成全量回归，详见 docs/07-部署说明.md。
--
-- 用法：
--   mysql -u root -p -e "CREATE DATABASE se_emoji CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
--   mysql -u root -p se_emoji < db/schema_mysql.sql

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- users
CREATE TABLE users (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	username VARCHAR(32) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(32) NOT NULL, 
	email VARCHAR(120), 
	status VARCHAR(32) NOT NULL, 
	auth_version INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	CONSTRAINT role_enum CHECK (`role` IN ('STUDENT', 'TEACHER', 'ADMIN')), 
	CONSTRAINT user_status_enum CHECK (status IN ('ACTIVE', 'DISABLED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE INDEX ix_users_role ON users (`role`);
CREATE INDEX ix_users_status ON users (status);

-- audit_logs
CREATE TABLE audit_logs (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	actor_id BIGINT, 
	action VARCHAR(60) NOT NULL, 
	target_type VARCHAR(40), 
	target_id VARCHAR(60), 
	result VARCHAR(20) NOT NULL, 
	detail TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_audit_result CHECK (result IN ('SUCCESS', 'FAILURE')), 
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

-- courses
CREATE TABLE courses (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	name VARCHAR(80) NOT NULL, 
	teacher_id BIGINT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_course_name_teacher UNIQUE (name, teacher_id), 
	FOREIGN KEY(teacher_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE INDEX ix_courses_teacher_id ON courses (teacher_id);

-- class_sessions
CREATE TABLE class_sessions (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	course_id BIGINT NOT NULL, 
	class_name VARCHAR(60) NOT NULL, 
	room VARCHAR(60), 
	start_at DATETIME NOT NULL, 
	end_at DATETIME NOT NULL, 
	cancelled BOOL NOT NULL, 
	ai_threshold FLOAT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE INDEX ix_session_course_start ON class_sessions (course_id, start_at);
CREATE INDEX ix_session_start_end ON class_sessions (start_at, end_at);

-- emoji_records
CREATE TABLE emoji_records (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	event_id VARCHAR(36) NOT NULL, 
	session_id BIGINT NOT NULL, 
	user_id BIGINT, 
	emotion VARCHAR(32) NOT NULL, 
	source VARCHAR(32) NOT NULL, 
	confidence FLOAT, 
	device_id VARCHAR(60), 
	model_version VARCHAR(60), 
	observed_at DATETIME NOT NULL, 
	received_at DATETIME NOT NULL, 
	manual_slot BIGINT, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_emoji_manual_slot UNIQUE (user_id, session_id, manual_slot), 
	CONSTRAINT ck_emoji_confidence_range CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)), 
	CONSTRAINT ck_emoji_manual_shape CHECK (source != 'MANUAL' OR (user_id IS NOT NULL AND confidence IS NULL AND device_id IS NULL)), 
	CONSTRAINT ck_emoji_ai_shape CHECK (source != 'AI' OR (user_id IS NULL AND manual_slot IS NULL AND confidence IS NOT NULL AND device_id IS NOT NULL)), 
	UNIQUE (event_id), 
	FOREIGN KEY(session_id) REFERENCES class_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT emotion_enum CHECK (emotion IN ('HAPPY', 'NEUTRAL', 'SAD', 'ANGRY', 'SURPRISED', 'FEARFUL', 'DISGUST')), 
	CONSTRAINT source_enum CHECK (source IN ('MANUAL', 'AI'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE INDEX ix_emoji_session_observed ON emoji_records (session_id, observed_at);
CREATE INDEX ix_emoji_source_observed ON emoji_records (source, observed_at);
CREATE INDEX ix_emoji_user_observed ON emoji_records (user_id, observed_at);

-- schedule_users
CREATE TABLE schedule_users (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	session_id BIGINT NOT NULL, 
	user_id BIGINT NOT NULL, 
	arranged_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_schedule_session_user UNIQUE (session_id, user_id), 
	FOREIGN KEY(session_id) REFERENCES class_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;
