# Makefile for ramses_cc development

# Configuration - Update these paths to match your environment
SOURCE_DIR := $(HOME)/dev/ramses_cc/custom_components/ramses_cc
HASS_DEV_DIR ?= $(HOME)/docker_files/hass
HASS_CONFIG_DIR ?= $(HASS_DEV_DIR)/config
HASS_CUSTOM_COMPONENTS_DIR ?= $(HASS_CONFIG_DIR)/custom_components
TARGET_DIR ?= $(HASS_CUSTOM_COMPONENTS_DIR)/ramses_cc

# Source files to copy
SOURCE_FILES = \
	__init__.py \
	binary_sensor.py \
	broker.py \
	climate.py \
	config_flow.py \
	const.py \
	icons.json \
	remote.py \
	schemas.py \
	number.py \
	sensor.py \
	water_heater.py \
	services.yaml \
	manifest.json \
	translations/en.json \
	translations/nl.json

# Test files (optional)
TEST_FILES = \
	tests/tests_new/test_set_fan_param.py \
	tests/tests_new/test_fan_param.py \
	tests/tests_new/test_init.py \
	tests/tests_new/conftest.py \
	tests/tests_new/snapshots/test_init.ambr

.PHONY: install install_rf test clean

# Main install target
install: check-env
	@echo "Installing ramses_cc from $(SOURCE_DIR) to $(TARGET_DIR)"
	@mkdir -p $(TARGET_DIR)
	@for file in $(SOURCE_FILES); do \
		echo "Copying $$file..."; \
		install -Dm644 "$(SOURCE_DIR)/$$file" "$(TARGET_DIR)/$$(basename "$$file")"; \
	done
	@echo "Installation complete. Restart Home Assistant to apply changes."

# Install test files as well
install-tests: install
	@echo "Installing test files..."
	@mkdir -p "$(TARGET_DIR)/tests/tests_new/snapshots"

# Copy ramses_rf and ramses_tx packages to Home Assistant container
install_rf:
	@echo "Copying ramses_rf and ramses_tx to Home Assistant container..."
	# Clean up any existing installation
	docker exec hass rm -rf /usr/local/lib/python3.13/site-packages/ramses_rf
	docker exec hass rm -rf /usr/local/lib/python3.13/site-packages/ramses_tx
	# Create directories
	docker exec hass mkdir -p /usr/local/lib/python3.13/site-packages/ramses_rf
	docker exec hass mkdir -p /usr/local/lib/python3.13/site-packages/ramses_tx
	# Copy ramses_rf package
	docker cp /home/willem/dev/ramses_rf/src/ramses_rf/. hass:/usr/local/lib/python3.13/site-packages/ramses_rf/
	# Copy ramses_tx package (flatten the structure)
	docker cp /home/willem/dev/ramses_rf/src/ramses_tx/. hass:/usr/local/lib/python3.13/site-packages/ramses_tx/
	# Fix permissions
	docker exec hass chmod -R a+rX /usr/local/lib/python3.13/site-packages/ramses_rf
	docker exec hass chmod -R a+rX /usr/local/lib/python3.13/site-packages/ramses_tx
	@echo "Installation complete."

# Check if required environment variables are set
check-env:
	@if [ ! -d "$(HASS_DEV_DIR)" ]; then \
		echo "Error: HASS_DEV_DIR ($(HASS_DEV_DIR)) does not exist"; \
		exit 1; \
	fi
	@if [ ! -d "$(HASS_CONFIG_DIR)" ]; then \
		echo "Error: HASS_CONFIG_DIR ($(HASS_CONFIG_DIR)) does not exist"; \
		echo "Please set HASS_CONFIG_DIR to your Home Assistant configuration directory"; \
		exit 1; \
	fi

# Run tests
test:
	@pytest tests/tests_new -v

# Clean up
clean:
	@echo "Cleaning up..."
	@find . -name "__pycache__" -type d -exec rm -r {} +
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@find . -name "*.pyd" -delete
	@find . -name "*.py,cover" -delete

# Show help
help:
	@echo "Available targets:"
	@echo "  install      - Install ramses_cc to Home Assistant custom_components"
	@echo "  install-test - Install ramses_cc with test files"
	@echo "  test         - Run tests"
	@echo "  clean        - Clean up Python cache files"
	@echo "  help         - Show this help message"

.DEFAULT_GOAL := help
