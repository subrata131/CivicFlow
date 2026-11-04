CREATE DATABASE IF NOT EXISTS waterlogging_tracker
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE waterlogging_tracker;

CREATE TABLE citizens (
  citizen_id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  phone VARCHAR(15) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  address VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admins (
  admin_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(60) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE departments (
  department_id INT AUTO_INCREMENT PRIMARY KEY,
  department_name VARCHAR(100) NOT NULL UNIQUE,
  description VARCHAR(255)
);

CREATE TABLE workers (
  worker_id INT AUTO_INCREMENT PRIMARY KEY,
  worker_name VARCHAR(100) NOT NULL,
  phone VARCHAR(15) NOT NULL,
  department_id INT,
  CONSTRAINT fk_worker_department FOREIGN KEY (department_id)
    REFERENCES departments(department_id) ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE complaints (
  complaint_id INT AUTO_INCREMENT PRIMARY KEY,
  citizen_id INT NOT NULL,
  location VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  priority ENUM('Low','Medium','High') NOT NULL DEFAULT 'Medium',
  status ENUM('Pending','In Progress','Resolved') NOT NULL DEFAULT 'Pending',
  photo_path VARCHAR(255),
  complaint_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_complaint_citizen FOREIGN KEY (citizen_id)
    REFERENCES citizens(citizen_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  INDEX idx_complaint_status (status),
  INDEX idx_complaint_date (complaint_date)
);

CREATE TABLE assignments (
  assignment_id INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT NOT NULL,
  worker_id INT NOT NULL,
  assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completion_date DATETIME NULL,
  CONSTRAINT fk_assignment_complaint FOREIGN KEY (complaint_id)
    REFERENCES complaints(complaint_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_assignment_worker FOREIGN KEY (worker_id)
    REFERENCES workers(worker_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE complaint_status_history (
  history_id INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT NOT NULL,
  old_status VARCHAR(30),
  new_status VARCHAR(30) NOT NULL,
  changed_by VARCHAR(60) NOT NULL,
  changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_history_complaint FOREIGN KEY (complaint_id)
    REFERENCES complaints(complaint_id) ON UPDATE CASCADE ON DELETE CASCADE
);
