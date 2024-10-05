#!/usr/bin/python3
#
###############################################################################
#
# bodeplot.py
#
# Usage: python3 bodeplot.py [-h] [--port PORT] [--fstart FSTART]
#                   [--fstop FSTOP][--fstep FSTEP] [--filename FILENAME]
#
# Create and save a bodeplot using a computer soundcard and
# Hantek 6022 oscilloscope
#
# options:
#  -h, --help           show this help message and exit
#  --port PORT          Serial port for the function generator. Default
#                       /dev/ttyUSB0.
#  --fstart FSTART      Starting frequency for the bodeplot in Hz. Default 10
#                       Hz.
#  --fstop FSTOP        Stopping frequency for the bodeplot in Hz. Default 5
#                       MHz.
#  --fstep FSTEP        Step frequency multiplier. Default 1.1.
#  --filename FILENAME  Filename to save the bodeplot information. Default
#                       bodeplot.csv.
#
#
# Utilizes computer soundcard and a Hantek 6022 to sweep
# a filter from 10 Hz to XXHz and create a bode frequency response plot
# and save the plot information to 'bode.csv'. Channel 1 on the oscilloscope
# is the filter output and Channel 2 on the oscilloscope is the filter input
# (i.e. the function generator output).
#
# Depends on having the Hantek6022API.
#
# https://github.com/Ho-Ro/Hantek6022API
#
# Author: Jonathan Weaver, jonw0224@gmail.com
# Date: 9/30/2024
# Version:
# 9/23/2024 - 1.00 - Created the file by following the examples for the libaries
# 9/30/2024 - 1.01 - Added arguments and argument parsing so the port, start
#                    frequency, stop frequency, frequency step, and save
#                    filename as arguments rather than hardcoded.
#
# Copyright (C) 2024 Jonathan Weaver
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###############################################################################

# Imports and dependencies
from PyHT6022.LibUsbScope import Oscilloscope
import numpy as np
import matplotlib.pyplot as plt
import pylab
import time
import sys
import argparse
import math
import csv
from pysinewave import SineWave
#disable smooth frequency transitions
sinewave = SineWave(pitch_per_second = 99999)
#helpfile
outfile      = open("outfile.csv", "w")
# Declare Global Constants
channelGain = 10 # Channel Gain, 10 is the highes gain, used here for more precise measurements
samplerates = (20, 32, 50, 64, 100, 128, 200, 500, 1000, 2000, 4000, 8000, 10000) # Valid samplerates in kilo samples per second
blocks = 20 # Number of 1024 samples to capture

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser(
    prog='bodeplot.py',
    description='Create and save a bodeplot using a computer soundcard and Hantek 6022 oscilloscope' )
ap.add_argument( "--fstart", type = int, default=30, help = "Starting frequency for the bodeplot in Hz. Default 10 Hz." )
ap.add_argument( "--fstop", type = int, default = 15000, help="Stopping frequency for the bodeplot in Hz. Default 5 MHz." )
ap.add_argument( "--fstep", type = float, default = 1.05, help="Step frequency multiplier. Default 1.1." )
ap.add_argument( "--filename", default = "bodeplot.csv", help="Filename to save the bodeplot information. Default bodeplot.csv." )

options = ap.parse_args()

# Setup Function Generator
# Create place to hold data from the Oscilloscope capture
data_points = blocks * 1024

# Skip the first 2K samples due to unstable transfer from oscilloscope
skip = 2 * 1024
data_points += skip

# Setup Oscilloscope
scope = Oscilloscope()
scope.setup()
scope.open_handle()

# Upload correct firmware into device's RAM
if (not scope.is_device_firmware_present):
    scope.flash_firmware()

# Scope configuration
scope.set_num_channels(2) # Two channels
# Setup channel 1
scope.set_ch1_voltage_range(channelGain) # Highest Gain
scope.set_ch1_ac_dc(scope.DC) # DC coupling
# Setup channel 2
scope.set_ch2_voltage_range(channelGain) # Highest Gain
scope.set_ch2_ac_dc(scope.DC) # DC coupling

# Start frequency
freq = options.fstart
sinewave.play()
# Save bodeplot data
data = []

while(freq < options.fstop):
    sinewave.set_frequency(freq)
    print(freq)
    # Calculate the sample rate to use for the scope
    samplerate_target = 4*freq
    samplerate = samplerates[0]
    for sr in samplerates:
        if samplerate < samplerate_target:
            samplerate = sr
    # Calculate and set the sample rate ID from real sample rate value
    if samplerate < 1e3:
        sample_id = int( round( 100 + samplerate / 10 ) ) # 20k..500k -> 102..150
    else:
        sample_id = int( round( samplerate / 1e3 ) ) # 1000k -> 1
    scope.set_sample_rate(sample_id)

    # Set the function generator waveform



    # Read and apply scope calibration values
    calibration = scope.get_calibration_values()

    # Wait a 10th of a second for things to settle out with the function generator and scope
    time.sleep(0.08)

    # Capture the waveforms on channel 1 and channel 2
    ch1_data, ch2_data = scope.read_data(data_points)#,raw=True)#timeout=1)
    voltage_data1 = scope.scale_read_data(ch1_data[skip:], channelGain, channel=1 )
    outfile      = open("outfile.csv", "w")
    #outfile.write(str(voltage_data1))
    voltage_data2 = scope.scale_read_data(ch2_data[skip:], channelGain, channel=2 )
    timing_data, rate_label = scope.convert_sampling_rate_to_measurement_times(data_points-skip, sample_id)
    outfile.write(str(timing_data))

    # Calculate the RMS value and DC value
    rms1 = 0
    dc1 = 0
    n1 = 0
    for v in voltage_data1:
        rms1 = rms1 + v*v
        dc1 = dc1 + v
        n1 = n1 + 1
    rms1 = math.sqrt(rms1/n1) - dc1/n1

    # Calculate the RMS value and DC value
    rms2 = 0
    dc2 = 0
    n2 = 0
    for v in voltage_data2:
        rms2 =rms2 + v*v
        dc2 = dc2 + v
        n2 = n2 + 1
    rms2 = math.sqrt(rms2/n2) - dc2/n2

    # Compute the FFT for Channel 1
    fft_values = np.fft.fft(voltage_data1)
    N = len(voltage_data1)  # Number of samples
    frequencies = np.fft.fftfreq(N, 1/samplerate/1000)  # Frequency bins

    # Compute the magnitude and phase of the FFT
    fft_magnitude = np.abs(fft_values)[:N // 2] / N  # Magnitude (positive frequencies)
    fft_phase = np.angle(fft_values)[:N // 2]  # Phase (positive frequencies)
    frequencies = frequencies[:N // 2]  # Positive frequency range

    # Find the index of the fundamental frequency (largest magnitude component)
    fundamental_index = np.argmax(fft_magnitude[1:]) + 1  # Skip the DC component (index 0)

    # Fundamental frequency, magnitude, and phase
    fundamental_frequency = frequencies[fundamental_index]
    fundamental_magnitude = fft_magnitude[fundamental_index]
    fundamental_phase = fft_phase[fundamental_index]

    # Compute the FFT for Channel 2
    fft_values = np.fft.fft(voltage_data2)
    N = len(voltage_data2)  # Number of samples
    frequencies = np.fft.fftfreq(N, 1/samplerate/1000)  # Frequency bins

    # Compute the magnitude and phase of the FFT
    fft_magnitude = np.abs(fft_values)[:N // 2] / N  # Magnitude (positive frequencies)
    fft_phase = np.angle(fft_values)[:N // 2]  # Phase (positive frequencies)
    frequencies = frequencies[:N // 2]  # Positive frequency range

    # Find the index of the fundamental frequency (largest magnitude component)
    fundamental_index = np.argmax(fft_magnitude[1:]) + 1  # Skip the DC component (index 0)

    # Fundamental frequency, magnitude, and phase
    fundamental_frequency2 = frequencies[fundamental_index]
    fundamental_magnitude2 = fft_magnitude[fundamental_index]
    fundamental_phase2 = fft_phase[fundamental_index]

    # Calculate the phase difference
    deltaphase = fundamental_phase - fundamental_phase2
    if deltaphase > math.pi:
        deltaphase = deltaphase - 2*math.pi
    if deltaphase < -math.pi:
        deltaphase = deltaphase + 2*math.pi

    # Save the bode plot data
    data.append([freq, rms1, rms2, rms1/rms2, deltaphase])

    # Next frequency
    freq = freq*options.fstep

# Close the scope
scope.close_handle()
sinewave.stop()

# Save the bodeplot data as a CSV file
with open(options.filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Frequency", "Channel 1 RMS Magnitude", "Channel 2 RMS Magnitude", "Gain (Ch1/Ch2)", "Phase Difference"])
    writer.writerows(data)

# Extract the bodeplot data for plotting
data_array = np.array(data)
frequencies = data_array[:,0]
gains = data_array[:,3]
phase = data_array[:,4]*180/math.pi

# Create a figure and two subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7))  # 2 rows, 1 column

# Create a log-log plot for the magnitude
ax1.loglog(frequencies, gains,)  # Use log-log scale

# Add labels and title
ax1.set_title("Magnitude Frequency Response")
# ax1.set_xlabel("Frequency in Hz (log scale)")
ax1.set_ylabel("Gain Magnitude (log scale)")

# Show grid
ax1.grid(True, which="both", linestyle="--", linewidth=0.5)

# Create a semi-log plot for the phase
ax2.semilogx(frequencies, phase, color='blue')  # Semilog y-axis

# Add labels and title
ax2.set_title("Phase Frequency Response")
ax2.set_xlabel("Frequency in Hz (log scale)")
ax2.set_ylabel("Phase Shift in Degrees")

# Show grid
ax2.grid(True, which="both", linestyle="--", linewidth=0.5)

ax2 = plt.gca()

ax2.set_ylim([90, -90])



# Display the plot
plt.show()

