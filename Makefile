.DEFAULT_GOAL := help

.PHONY: help radio-test decode-recording
help:
	@echo "make radio-test  Transmit the Declaration clip once (keys the radio)."
	@echo 'make decode-recording RECORDING="/path/to/audio.m4a"  Analyze offline.'

OUTPUT ?= artifacts/radio/recording-analysis
decode-recording:
	@test -n "$(RECORDING)" || (echo 'Set RECORDING="/path/to/audio.m4a"'; exit 1)
	uv run --locked python -m lab.recording "$(RECORDING)" --equalize --output "$(OUTPUT)"

# Frequency is metadata only; manually tune both radios to 146.580 MHz.
# Start your recorder and check that the channel is clear before running.
radio-test:
	uv run --extra radio --locked python -m lab.radio transmit \
		artifacts/radio/declaration-opening-fsk4.wav \
		--device 'USB PnP Sound Device' \
		--port /dev/cu.usbserial-2120 \
		--frequency-mhz 146.580 \
		--gain 0.2 \
		--execute
