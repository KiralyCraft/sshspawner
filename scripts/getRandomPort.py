import socket

def get_random_port():
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def main():
    print(get_random_port())

if __name__ == "__main__":
    main()
