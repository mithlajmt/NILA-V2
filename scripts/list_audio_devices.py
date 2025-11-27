import speech_recognition as sr

def list_devices():
    print("Available Audio Devices:")
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"Index {index}: {name}")

if __name__ == "__main__":
    list_devices()
