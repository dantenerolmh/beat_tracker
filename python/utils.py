import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.io import wavfile
import IPython.display as ipd
import pickle
import torch


data = pd.read_csv('../data/data.csv', index_col=0)


def clicks(times=None, sr=44100, length=None):
    positions = (np.asanyarray(times) * sr).astype(int)

    click_freq=1000.0
    click_duration=0.1

    angular_freq = 2 * np.pi * click_freq / float(sr)

    click = np.logspace(0, -10,
                        num=int(np.round(sr * click_duration)),
                        base=2.0)

    click *= np.sin(angular_freq * np.arange(len(click)))

    if length is None:
        length = positions.max() + click.shape[0]
    else:
        positions = positions[positions < length]

    click_signal = np.zeros(length, dtype=np.float32)

    for start in positions:
        end = start + click.shape[0]

        if end >= length:
            click_signal[start:] += click[:length - start]
        else:
            click_signal[start:end] += click

    return click_signal


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def remix(signal, num_channels=1):
    if num_channels == signal.ndim:
        return signal
    elif num_channels == 1 and signal.ndim > 1:
        # down-mix to mono
        return np.mean(signal, axis=-1).astype(signal.dtype)
    elif num_channels > 1 and signal.ndim == 1:
        # up-mix a mono signal simply by copying channels
        return np.tile(signal[:, np.newaxis], num_channels)
    else:
        raise NotImplementedError("Requested %d channels, but got %d channels "
                                  "and channel conversion is not implemented."
                                  % (num_channels, signal.shape[1]))


def get_dataset(idx):
    if idx == 1: return 'Ballroom'
    elif idx == 2: return 'SMC'
    elif idx == 3: return 'Hainsworth'
    elif idx == 4: return 'GTZAN'
    elif idx == 5: return 'Beatles'
    elif idx == 6: return 'MIREX'
    else: return None


def index_to_file(index):
    file = data.at[index, 'file']
    idx = data.at[index, 'data_set']
    dataset = get_dataset(idx)
    return file, dataset


def get_audio(input, normalize=False):
    file, dataset = index_to_file(input)
    _, signal = wavfile.read('../data/audio/{}/{}.wav'.format(dataset, file), mmap=False)

    if normalize: signal = signal / np.max(np.abs(signal))
    return signal


def get_signal(input, normalize=False):
    return get_audio(input, normalize=False)


def read_wav(input, normalize=False):
    file, dataset = index_to_file(input)
    sr, signal = wavfile.read('../data/audio/{}/{}.wav'.format(dataset, file), mmap=False)

    if normalize: signal = signal / np.max(np.abs(signal))
    return sr, signal


def get_sample_rate(file):
    file, dataset = index_to_file(input)
    sr, _ = wavfile.read('../data/audio/{}/{}.wav'.format(dataset, file), mmap=False)
    return sr


def play_audio(input, normalize=False, xlim=None):
    sr, signal = read_wav(input, normalize=False)
    if xlim:
        signal = signal[int(xlim[0]*sr):int(xlim[1]*sr)]  
    return ipd.Audio(signal, rate=sr)


def get_input(input):
    file, dataset = index_to_file(input)
    return pickle.load(open('../data/inputs/{}/{}.npy'.format(dataset, file), 'rb'))


def get_labels(input):
    file, dataset = index_to_file(input)
    return pickle.load(open('../data/labels/{}/{}.npy'.format(dataset, file), 'rb'))


def get_annotations(input):
    file, dataset = index_to_file(input)
    return np.loadtxt('../data/annotations/{}/{}.beats'.format(dataset, file), 
        ndmin=2)[:, 0]


def get_predictions(input, subfolder):
    file, dataset = index_to_file(input)
    return np.loadtxt('../data/predictions/{}/{}/{}.beats'.format(subfolder, dataset, file))


def play_annotations(input, modified=False, normalize=True, xlim=None):
    file, dataset = index_to_file(input)

    sr, signal = wavfile.read('../data/audio/{}/{}.wav'.format(dataset, file), mmap=False)
    
    if normalize:
        signal = signal / np.max(np.abs(signal))

    if modified:
        annotations = np.loadtxt('../data/annotations/modified/{}.beats'.format(file), 
        ndmin=2)[:, 0] 
        metronome = clicks(annotations, sr=sr, length=len(signal))   
    else:
        metronome = clicks(get_annotations(input), sr=sr, length=len(signal))

    signal = signal + metronome    
    signal = signal / np.max(np.abs(signal))

    if xlim:
        signal = signal[int(xlim[0]*sr):int(xlim[1]*sr)]  
        
    return ipd.Audio(signal, rate=sr)


def play_predictions(input, subfolder, normalize=True, xlim=None):
    file, dataset = index_to_file(input)

    sr, signal = wavfile.read('../data/audio/{}/{}.wav'.format(dataset, file), mmap=False)
    
    if normalize:
        signal = signal / np.max(np.abs(signal))
        
    metronome = clicks(get_predictions(input, subfolder), sr=sr, length=len(signal))

    signal = signal + metronome
        
    signal = signal / np.max(np.abs(signal))

    if xlim:
        signal = signal[int(xlim[0]*sr):int(xlim[1]*sr)]  
        
    return ipd.Audio(signal, rate=sr)


def get_activations(input, model):
    file, dataset = index_to_file(input)
    feature = get_input(input)

    with torch.no_grad():
        out = model(feature.view(1, len(feature),-1))

    return np.exp(np.array(out[0,1,:]))


def show_activations(input, model, subfolder, xlim=None, show_annotations=True, show_predictions=True):
    file, dataset = index_to_file(input)

    feature = get_input(input)

    annotations = get_annotations(input)
    predictions = get_predictions(input, subfolder)

    with torch.no_grad():
        out = model(feature.view(1, len(feature),-1))

    activations = np.exp(np.array(out[0,1,:]))

    plt.figure(figsize=(4,1))
    plt.plot(activations)
    plt.xlim(0, len(activations))
    plt.ylim(0, 1)
    plt.xlabel('Frames')
    plt.ylabel('Activation')
    if show_annotations:
        for ann in annotations:
            plt.axvline(x=ann*100, color='k', linestyle=':', linewidth=1)
    if show_predictions:
        for ann in predictions:
            plt.axvline(x=ann*100, color='r', linestyle=':', linewidth=1)
    if xlim:
        plt.xlim(int(xlim[0]*100), int(xlim[1]*100))
    plt.tight_layout()


def plot_audio(input, xlim=None):

    file, dataset = index_to_file(input)

    sr, signal = wavfile.read('../data/audio/{}/{}.wav'.format(dataset, file), mmap=False)

    annotations = get_annotations(input)

    time_vec = np.linspace(0, len(signal)/sr, len(signal))

    signal = signal / np.max(np.abs(signal))

    plt.figure(figsize=(4,1))
    plt.plot(time_vec, signal);
    plt.xlabel('Time [s]')
    plt.ylabel('Amplitude')
    if xlim: 
        plt.xlim(xlim)

    for ann in annotations:
        plt.axvline(x=ann, color='k', linestyle=':', linewidth=1)
    plt.tight_layout()





