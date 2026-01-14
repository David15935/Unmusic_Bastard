queue = []

def add_to_queue(song):
    queue.append(song)

def get_queue():
    return queue

def skip_song():
    if queue:
        queue.pop(0)
        return queue[0] if queue else None
