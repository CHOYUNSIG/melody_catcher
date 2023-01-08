import numpy as np
import pyaudio
import threading

lock = threading.Lock()



audio_data = None



class audio_importer():

    def __init__(self, sample_rate, fps, chunk):
        self.sample_rate = sample_rate
        self.chunk = chunk
        self.method = int(np.ceil(chunk / (sample_rate / fps)))
        self.streams = []
        for _ in range(self.method):
            p = pyaudio.PyAudio()
            self.streams.append(p.open(format=pyaudio.paInt16, channels=1, rate=self.sample_rate, input=True, frames_per_buffer=chunk))
        self.stream_index = 0
        global audio_data
        audio_data = np.array([0] * self.chunk)
        return

    def get_audio_data(self):
        return np.array(audio_data)

    def get_audio_delay(self):
        return self.chunk / self.sample_rate

    def importer(self):
        try:
            threading.Thread(target=audio_import_method, args=(self.streams[self.stream_index], self.chunk)).start()
        except:
            pass
        self.stream_index = (self.stream_index + 1) % self.method 


def audio_import_method(stream, size):
    data = np.append([], np.frombuffer(stream.read(size), dtype=np.int16))
    global audio_data
    lock.acquire()
    audio_data = data
    lock.release()
    return
