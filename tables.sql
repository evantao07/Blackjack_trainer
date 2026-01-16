-- Active: 1768541672863@@127.0.0.1@3306
CREATE DATABASE IF NOT EXISTS blackjack;
USE blackjack;

-- Stores chart settings (you can have multiple charts)
CREATE TABLE IF NOT EXISTS bj_chart (
  chart_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  notes VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Only Hit/Stand decisions
CREATE TABLE IF NOT EXISTS bj_hit_stand (
  chart_id INT NOT NULL,
  hand_kind ENUM('HARD','SOFT') NOT NULL,
  player_total TINYINT NOT NULL,
  dealer_upcard ENUM('2','3','4','5','6','7','8','9','10','A') NOT NULL,
  action ENUM('H','S') NOT NULL,
  PRIMARY KEY (chart_id, hand_kind, player_total, dealer_upcard),
  FOREIGN KEY (chart_id) REFERENCES bj_chart(chart_id) ON DELETE CASCADE
);

-- One run of the game = one session
CREATE TABLE IF NOT EXISTS bj_session (
  session_id INT AUTO_INCREMENT PRIMARY KEY,
  chart_id INT NOT NULL,
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TIMESTAMP NULL,
  FOREIGN KEY (chart_id) REFERENCES bj_chart(chart_id)
);

-- Logs every player decision (for accuracy)
CREATE TABLE IF NOT EXISTS bj_decision_log (
  log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  hand_kind ENUM('HARD','SOFT') NOT NULL,
  player_total TINYINT NOT NULL,
  dealer_upcard ENUM('2','3','4','5','6','7','8','9','10','A') NOT NULL,
  player_action ENUM('H','S') NOT NULL,
  correct_action ENUM('H','S') NOT NULL,
  is_correct BOOLEAN NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES bj_session(session_id) ON DELETE CASCADE
);

SHOW tables;