#                    )      )   (      (
#                 ( /(   ( /(   )\ )   )\ )
#       (   (     )\())  )\()) (()/(  (()/(
#       )\  )\  |((_)\  ((_)\   /(_))  /(_))
#      ((_)((_) |_ ((_)  _((_) (_))   (_))_
#      \ \ / /  | |/ /  | || | / __|   |   \
#       \ V /     ' <   | __ | \__ \   | |) |
#        \_/     _|\_\  |_||_| |___/   |___/

import librosa
import numpy as np
import soundfile as sf
import os
from tqdm import tqdm

amount = input("Enter amount:")

output_dir = "AntiClipper"

input_file = f"{output_dir}/input.wav"


def return_zero_on_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            return 0

    return wrapper


def MOD(n):
    """INPUT YOUR DESIRED FUNCTION IN HERE.
    THIS FUNCTION SHOULD RELY ON USING OMEGA, THE CONSTANT FOR TRIG FUNCTIONS
    WHEN DIGITALLY PROCESSING SIGNALS. OMEGA IS DEFAULTED TO BE:
    2*PI/SAMPLE_RATE SO DO NOT INCLUDE IT IN THIS FUNCTION
    IT SHOULD ALSO BE A FUNCTION OF RANGE [-1, 1]"""
    n_float = float(n)

    abs_sin_n = np.abs(np.sin(n_float))

    result = np.power(abs_sin_n, float(amount))

    return result


def MOD2(n):
    """INPUT YOUR DESIRED FUNCTION IN HERE.
    THIS FUNCTION SHOULD BE THE SCALED DERIVATIVE OF THE AFOREMENTIONED MOD FUNCTION"""
    n_float = float(n)

    abs_sin_n = np.abs(np.cos(n_float))

    result = np.power(abs_sin_n, float(amount))

    return result


def read_wav_to_array(filename):
    """Read a WAV file and convert it to an array of numbers in the range [-1, 1]"""
    y, sr = librosa.load(filename, sr=None, mono=False)
    return y, sr


def find_regions(array):
    regions = []
    prev_sign = np.sign(array[0])
    start_index = 0

    for n in range(1, len(array)):
        current_sign = np.sign(array[n])

        if current_sign != prev_sign:
            end_index = n - 1
            regions.append((prev_sign, start_index, end_index))
            start_index = n
            prev_sign = current_sign

    regions.append((prev_sign, start_index, len(array) - 1))

    return regions


def process_audio_file(input_file):
    audio_data, sr = read_wav_to_array(input_file)
    audio_channel_l, audio_channel_r, audio_channel_m = None, None, None
    if len(audio_data.shape) == 2 and audio_data.shape[0] == 2:
        audio_channel_l, audio_channel_r = audio_data
    else:
        audio_channel_m = audio_data

    if audio_channel_l is not None:
        print("Left Channel:", audio_channel_l, len(audio_channel_l))
    if audio_channel_r is not None:
        print("Right Channel:", audio_channel_r, len(audio_channel_r))
    if audio_channel_m is not None:
        print("Mono Channel:", audio_channel_m)

    return sr, audio_channel_l, audio_channel_r, audio_channel_m


def anticlip(array: list, regions: list):
    appendion = []
    with tqdm(total=len(regions),
              bar_format='{l_bar}\033[91m{bar}\033[0m{r_bar}',
              position=0,
              leave=True) as pbar:

        for region_idx, (sign, the, end) in enumerate(regions):
            hosv = the + np.argmax(array[the:end]) if end > the else -1
            if hosv == -1:
                appendion.append(0)
                continue

            original_length = end - the + 1
            processed_length = 0

            for idx in range(hosv - the + 1):
                omega2 = 2 * np.pi / max(1, (hosv - the + 1) * 4)
                multiplier = MOD(omega2 * idx)
                result = sign * multiplier * array[the + idx]
                appendion.append(result)
                processed_length += 1

            for jdx in range(1, end - hosv + 1):
                omega2 = 2 * np.pi / max(1, (end - hosv) * 4)
                multiplier = MOD2(omega2 * jdx)
                result = sign * multiplier * array[hosv + jdx]
                appendion.append(result)
                processed_length += 1

            if original_length != processed_length:
                print(f"Error found @{region_idx + 1}, {original_length},{processed_length}")
            pbar.update(1)

    return appendion


samplerate, audio_channel_l, audio_channel_r, audio_channel_m = process_audio_file(input_file)

results = []

if audio_channel_l is not None:
    regions_left = find_regions(audio_channel_l)
    abs_channel_left = abs(audio_channel_l)
    new_left_list = anticlip(abs_channel_left, regions_left)
    results.append(new_left_list)

if audio_channel_r is not None:
    regions_right = find_regions(audio_channel_r)
    abs_channel_right = abs(audio_channel_r)
    new_right_list = anticlip(abs_channel_right, regions_right)
    results.append(new_right_list)

if audio_channel_m is not None:
    regions_right = find_regions(audio_channel_m)
    abs_channel_right = abs(audio_channel_m)
    new_right_list = anticlip(abs_channel_right, regions_right)
    results.append(new_right_list)
    regions_left = find_regions(audio_channel_m)
    abs_channel_left = abs(audio_channel_m)
    new_left_list = anticlip(abs_channel_left, regions_left)
    results.append(new_left_list)

min_length = min(len(results[0]), len(results[1]))
results[0] = results[0][:min_length]
results[1] = results[1][:min_length]

results_np = np.array(results, dtype=np.float32)

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

output_path = os.path.join(output_dir, "output.wav")
sf.write(output_path, results_np.T, samplerate)


def find_skipped_numbers(regions):
    skipped = []
    for i in range(1, len(regions)):
        if regions[i][1] != regions[i - 1][2] + 1:
            skipped_range = (regions[i - 1][2] + 1, regions[i][1] - 1)
            skipped.append(skipped_range)
    return skipped


def regions_are_consecutive(regions):
    for i in range(1, len(regions)):
        if regions[i][1] != regions[i - 1][2] + 1:
            return False
    return True
