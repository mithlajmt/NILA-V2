import os
import contextlib
import ctypes
import logging

# Define C error handler type
ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)

def py_error_handler(filename, line, function, err, fmt):
    # Determine log level based on error code if possible, or just debug
    # We generally want to suppress these from stderr, but maybe log them to debug
    pass

c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

@contextlib.contextmanager
def no_alsa_error():
    """
    Context manager to suppress ALSA error messages.
    """
    try:
        asound = ctypes.cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler)
        yield
        asound.snd_lib_error_set_handler(None)
    except OSError:
        # Fallback if libasound is not found
        yield
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to suppress ALSA errors: {e}")
        yield
