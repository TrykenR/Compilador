class ManejoDeBuffers:
    def __init__(self, file_path, buffer_size=1024):
        self.file = open(file_path, "r")
        self.buffer_size = buffer_size
        self.buffer = ""
        self.position = 0

    def load_buffer(self):
        self.buffer = self.file.read(self.buffer_size)
        self.position = 0
        return len(self.buffer) > 0

    def get_char(self):
        if self.position >= len(self.buffer):
            if not self.load_buffer():
                return None
        char = self.buffer[self.position]
        self.position += 1
        return char
    