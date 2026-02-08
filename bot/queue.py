from collections import deque

_queues = {}
_playlists = {}


def _ensure_queue(chat_id):
    if chat_id not in _queues:
        _queues[chat_id] = deque()
    return _queues[chat_id]


def add_song(chat_id, song):
    _ensure_queue(chat_id).append(song)


def next_song(chat_id):
    q = _ensure_queue(chat_id)
    return q.popleft() if q else None


def list_queue(chat_id):
    return list(_ensure_queue(chat_id))


def clear_queue(chat_id):
    _queues[chat_id] = deque()


def _ensure_playlists(chat_id):
    if chat_id not in _playlists:
        _playlists[chat_id] = {}
    return _playlists[chat_id]


def create_playlist(chat_id, name):
    playlists = _ensure_playlists(chat_id)
    if name in playlists:
        return False
    playlists[name] = []
    return True


def list_playlists(chat_id):
    return sorted(_ensure_playlists(chat_id).keys())


def add_to_playlist(chat_id, name, item):
    playlists = _ensure_playlists(chat_id)
    if name not in playlists:
        return False
    playlists[name].append(item)
    return True


def get_playlist(chat_id, name):
    return _ensure_playlists(chat_id).get(name)


def remove_playlist(chat_id, name):
    playlists = _ensure_playlists(chat_id)
    if name in playlists:
        del playlists[name]
        return True
    return False


def remove_from_playlist(chat_id, name, index):
    playlists = _ensure_playlists(chat_id)
    if name not in playlists:
        return False
    items = playlists[name]
    if index < 0 or index >= len(items):
        return False
    items.pop(index)
    return True
