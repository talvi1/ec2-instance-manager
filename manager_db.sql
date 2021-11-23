
DROP SCHEMA IF EXISTS `manager`;

CREATE SCHEMA IF NOT EXISTS `manager` DEFAULT CHARACTER SET utf8 ;
USE `manager`;

DROP TABLE IF EXISTS `manager`.`scaling` ;

CREATE TABLE IF NOT EXISTS `manager`.`scaling` (
  `ID` INT NOT NULL AUTO_INCREMENT,
  `increase` VARCHAR(50) NOT NULL,
  `decrease` VARCHAR(50),
  `expand` VARCHAR(50), 
  `shrink` VARCHAR(50),
  `auto` VARCHAR(50), 
  PRIMARY KEY (`ID`)
)
ENGINE = InnoDB;

DROP TABLE IF EXISTS `manager`.`workers` ;

CREATE TABLE IF NOT EXISTS `manager`.`workers` (
  `ID` INT NOT NULL AUTO_INCREMENT,
  `numworker` VARCHAR(50) NOT NULL,
  `time` VARCHAR(50),
  PRIMARY KEY (`ID`)
)
ENGINE = InnoDB;
