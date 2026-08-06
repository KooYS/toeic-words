"""Range 요청을 지원하는 정적 서버.

python3 -m http.server 는 Range를 무시하고 항상 200 + 전체 파일을 준다.
그러면 브라우저가 mp3 중간으로 seek을 못 해서 단어 오프셋 재생이 0초부터 나간다.

  python3 serve.py          # http://localhost:8765
  python3 serve.py --check  # Range 파싱 자체 점검
"""
import http.server, os, re, sys

PORT = 8765


def slice_range(header, size):
    """Range 헤더 → (start, end) 포함 구간. 미지정/형식오류면 None, 범위밖이면 'invalid'."""
    m = re.fullmatch(r'bytes=(\d*)-(\d*)', (header or '').strip())
    if not m or m.group(1) == m.group(2) == '':
        return None
    a, b = m.groups()
    if a:
        start, end = int(a), int(b) if b else size - 1
    else:
        start, end = max(0, size - int(b)), size - 1      # bytes=-N : 끝에서 N바이트
    end = min(end, size - 1)
    return 'invalid' if start >= size or start > end else (start, end)


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().do_GET()
        with open(path, 'rb') as f:
            size = os.fstat(f.fileno()).st_size
            rng = slice_range(self.headers.get('Range'), size)
            if rng is None:
                return super().do_GET()
            if rng == 'invalid':
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.end_headers()
                return
            start, end = rng
            self.send_response(206)
            self.send_header('Content-Type', self.guess_type(path))
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.send_header('Content-Length', str(end - start + 1))
            self.end_headers()
            f.seek(start)
            left = end - start + 1
            while left:
                chunk = f.read(min(1 << 16, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)


def check():
    assert slice_range(None, 100) is None
    assert slice_range('bytes=0-', 100) == (0, 99)
    assert slice_range('bytes=10-19', 100) == (10, 19)
    assert slice_range('bytes=90-999', 100) == (90, 99)      # 끝 초과는 잘라냄
    assert slice_range('bytes=-30', 100) == (70, 99)         # 끝에서 30바이트
    assert slice_range('bytes=-500', 100) == (0, 99)
    assert slice_range('bytes=100-', 100) == 'invalid'       # 파일 크기 이상
    assert slice_range('bytes=50-40', 100) == 'invalid'
    assert slice_range('bytes=-', 100) is None
    assert slice_range('junk', 100) is None
    print('slice_range OK')


if __name__ == '__main__':
    if '--check' in sys.argv:
        check()
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        print(f'http://localhost:{PORT}')
        http.server.ThreadingHTTPServer(('', PORT), Handler).serve_forever()
