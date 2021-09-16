
import numpy as np
import pyaudio
import pygame
import time
import win32api
import win32gui


# 매개변수

TITLE = "Melody Catcher"

RATE = 44100
CHUNK_FFT = 1024 * 1
CHUNK_DRAW = 1024 * 1
START_FRAME = 1024 * 0

FPS = 60

HEIGHT_STATE = 30

WIDTH = 960
HEIGHT = HEIGHT_STATE+540

GRAPH_FFT_CX = 400
GRAPH_FFT_CY = 280
GRAPH_FFT_X = WIDTH - 20 - GRAPH_FFT_CX
GRAPH_FFT_Y = HEIGHT_STATE + 50

FREQ_MASK = 15

GRAPH_AUDIO_CY = 100
GRAPH_AUDIO_X = 20
GRAPH_AUDIO_Y = HEIGHT - GRAPH_AUDIO_CY - 30
GRAPH_AUDIO_CX = WIDTH - GRAPH_AUDIO_X * 2

GRAPH_PIANO_CX = 500
GRAPH_PIANO_CY = 50
GRAPH_PIANO_X = 20
GRAPH_PIANO_Y = HEIGHT_STATE + 150

THR_ATK_INIT = 5
THR_ATK = 10
THR_ATK_INIT_NORM = 0.1
THR_ATK_NORM = 0.3

# 프로세스 레퍼런스
HWND = None

# A-weighting 가중치 상수
A_CURVE = np.array([-100])
for _ in range(20):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]+49.5/20])
for _ in range(20):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]+15.9/20])
for _ in range(40):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]+12.1/40])
for _ in range(80):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]+9.1/80])
for _ in range(160):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]+6.8/160])
for _ in range(320):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]+4.7/320])
for _ in range(640):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]+2.5/640])
for _ in range(1280):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]+0.7/1280])
for _ in range(2560):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]-0.8/2560])
for _ in range(5120):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]-3.0/5120])
for _ in range(10240):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]-6.8/10240])
for _ in range(10240):
    A_CURVE = np.append(A_CURVE, [A_CURVE[-1]-100.0/10240])
A_CURVE = np.power(10, A_CURVE[:RATE//2]/20)*2

# 피아노 음계 진동수
PIANO_FREQS = np.array([27.5])
for _ in range(87):
    PIANO_FREQS = np.append(PIANO_FREQS, [PIANO_FREQS[-1]*2**(1/12)])

PIANO_TILE_TYPE = np.append(np.append([0,3,2,0,3,1,3,2,0,3,1,3], [1,3,2,0,3,1,3,2,0,3,1,3]*6), [1,3,2,4])

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=1)

pygame.init()
pygame.display.set_caption(TITLE)
pygame.display.set_icon(pygame.image.load("./icon_mc.png"))
clock = pygame.time.Clock()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)

text = []
text.append(pygame.font.Font("Pretendard-Thin.otf", 15).render("Melody Catcher", True, (255,255,255)))
text.append(pygame.font.Font("Pretendard-Thin.otf", 25).render("Audio signal", True, (255,255,255)))
text.append(pygame.font.Font("Pretendard-Thin.otf", 25).render("Spectrogram", True, (255,255,255)))
text.append(pygame.transform.rotate(pygame.font.Font("Pretendard-Regular.otf", 10).render("20Hz", True, (255,255,255)), 315))
text.append(pygame.transform.rotate(pygame.font.Font("Pretendard-Regular.otf", 10).render("100Hz", True, (255,255,255)), 315))
text.append(pygame.transform.rotate(pygame.font.Font("Pretendard-Regular.otf", 10).render("1kHz", True, (255,255,255)), 315))
text.append(pygame.transform.rotate(pygame.font.Font("Pretendard-Regular.otf", 10).render("10kHz", True, (255,255,255)), 315))
text.append(pygame.transform.rotate(pygame.font.Font("Pretendard-Regular.otf", 10).render("20kHz", True, (255,255,255)), 315))
text.append(pygame.font.Font("Pretendard-Regular.otf", 10).render("Sample start", True, (0,255,0)))
text.append(pygame.font.Font("Pretendard-Regular.otf", 10).render("Sample end", True, (255,0,0)))
text.append(pygame.font.Font("Pretendard-Regular.otf", 10).render("Raw", True, (255,255,255)))
text.append(pygame.font.Font("Pretendard-Regular.otf", 10).render("A-weighting", True, (255,255,255)))
text.append(pygame.font.Font("Pretendard-Thin.otf", 25).render("Melody", True, (255,255,255)))


win_x = None
win_y = None
mouseprepos = win32api.GetCursorPos()
mouse = win32api.GetCursorPos()
keyboardpre = pygame.key.get_pressed()
keyboard = pygame.key.get_pressed()

eventKey_capture = False
eventKey_disableWindow = False
eventKey_moveWindow = False
eventKey_quit = False

f = np.fft.fftfreq(n = RATE, d = 1/RATE)[:RATE//2].astype(np.int32)
audio_data = np.array([0]*CHUNK_DRAW)
fft_data = np.array([0]*len(f))
aweight_data = np.array([0]*len(f))
piano_data = np.array([[0]*88 for _ in range(2)])

max_head = 1e-10
max_head_norm = 1e-10
thr_time = time.time()
thr_time_norm = time.time()
thr_accel = 0
thr_accel_norm = 0

# 그래프 각 샘플의 x좌표 cache 
draw_audio_x = [GRAPH_AUDIO_X+int(np.round(GRAPH_AUDIO_CX*i/CHUNK_DRAW)) for i in range(CHUNK_DRAW)]
draw_fft_x = np.append([GRAPH_FFT_X]*FREQ_MASK, [GRAPH_FFT_X+int(np.round(np.log10(i-FREQ_MASK+1)*GRAPH_FFT_CX/np.log10(RATE/2))) for i in range(FREQ_MASK, RATE//2)])
draw_piano_x = [GRAPH_PIANO_X+int(np.round(i*GRAPH_PIANO_CX/156)) for i in range(156)]

pygame.display.flip()

# 프로세스 레퍼런스 업데이트
def callback(hwnd, extra):
    if win32gui.GetWindowText(hwnd) == TITLE:
        global HWND
        HWND = hwnd
win32gui.EnumWindows(callback, None)

win_x, win_y, _, _= win32gui.GetWindowRect(HWND)


while not eventKey_quit:

    clock.tick(FPS)

    # 이벤트 불러오기
    mouse = win32api.GetCursorPos()
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            eventKey_quit = True

        # 키보드 이벤트
        if event.type == pygame.KEYDOWN:
            keyboard = pygame.key.get_pressed()
            # ESC
            if keyboard[pygame.K_ESCAPE]:
                eventKey_quit = True
            # SPACEBAR
            if keyboard[pygame.K_SPACE] and not keyboardpre[pygame.K_SPACE]:
                eventKey_capture = not eventKey_capture

        if event.type == pygame.KEYUP:
            keyboard = pygame.key.get_pressed()

        # 마우스 이벤트
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 창 이동
            if win_x <= mouse[0] <= win_x + WIDTH - 120 and win_y <= mouse[1] <= win_y + 30:
                eventKey_moveWindow = True

        if event.type == pygame.MOUSEBUTTONUP:
            if eventKey_moveWindow:    
                eventKey_moveWindow = False
            # 닫기 버튼
            if win_x + WIDTH - 40 <= mouse[0] <= win_x + WIDTH and win_y + 0 <= mouse[1] <= win_y + 30:
                eventKey_quit = True
            # 최소화 버튼
            if win_x + WIDTH - 80 <= mouse[0] <= win_x + WIDTH - 40 and win_y + 0 <= mouse[1] <= win_y + 30:
                eventKey_disableWindow = True
                win32gui.ShowWindow(HWND, 6)
            # 캡처 버튼
            if win_x + WIDTH - 120 <= mouse[0] <= win_x + WIDTH - 80 and win_y + 0 <= mouse[1] <= win_y + 30:
                eventKey_capture = not eventKey_capture

    # 창 활성화    
    if eventKey_disableWindow:
        if win32gui.GetWindowRect(HWND)[0] >= -WIDTH:
            win32gui.ShowWindow(HWND, 9)
            eventKey_disableWindow = False

    # 창 이동
    if eventKey_moveWindow:
        win32gui.SetWindowPos(HWND, 0, win_x+mouse[0]-mouseprepos[0], win_y+mouse[1]-mouseprepos[1], WIDTH, HEIGHT+HEIGHT_STATE, 64)
        win_x, win_y, _, _ = win32gui.GetWindowRect(HWND)

    # 데이터 보관처리
    keyboardpre = keyboard
    mouseprepos = mouse

    # 데이터 가공

    # 오디오 데이터 불러오기
    audio_data = np.append(audio_data[CHUNK_DRAW:], np.frombuffer(stream.read(CHUNK_DRAW), dtype=np.int16))

    # 최대 헤드룸 조절
    temp_head = np.max(abs(audio_data))
    if max_head <= temp_head:
        thr_accel = max_head = temp_head
        thr_time = time.time()
    else:
        interval_time = time.time() - thr_time - THR_ATK_INIT
        if 0 < interval_time:
            max_head = max(int(thr_accel * (1 - interval_time / THR_ATK)), temp_head, 1e-10)

    # 푸리에 변환
    fft_data = np.abs(np.fft.fft(audio_data[START_FRAME: START_FRAME+CHUNK_FFT], RATE, norm="ortho")[:len(f)])*512/max_head/CHUNK_FFT

    # A-weighting 변환
    aweight_data = fft_data * A_CURVE

    # 피아노 배음 가중치 데이터
    piano_data = np.append(np.array([[sum([(
        (aweight_data[int(np.floor(PIANO_FREQS[i]*j))] + (aweight_data[int(np.floor(PIANO_FREQS[i]*j))]-aweight_data[int(np.floor(PIANO_FREQS[i]*j))-1]) * (PIANO_FREQS[i]*j-int(PIANO_FREQS[i]*j))) + \
        (aweight_data[int(np.ceil(PIANO_FREQS[i]*j))] + (aweight_data[int(np.ceil(PIANO_FREQS[i]*j))]-aweight_data[int(np.ceil(PIANO_FREQS[i]*j))+1]) * (1-PIANO_FREQS[i]*j+int(PIANO_FREQS[i]*j))) ) \
             / j for j in range(1, 5)]) for i in range(88)]]) ** 5, piano_data[:1], axis = 0)
    piano_data[0] = (piano_data[0] + piano_data[1])/2

    # 배음 가중치 정규화
    temp_head_norm = np.max(abs(piano_data[0]))
    if max_head_norm <= temp_head_norm:
        thr_accel_norm = max_head_norm = temp_head_norm
        thr_time_norm = time.time()
    else:
        interval_time = time.time() - thr_time_norm - THR_ATK_INIT_NORM
        if 0 < interval_time:
            max_head_norm = max(thr_accel_norm * (1 - interval_time / THR_ATK_NORM), temp_head_norm, 1e-10)
    
    
    # 화면 구성

    if not eventKey_capture:

        # 배경
        for i in range(HEIGHT):
            pygame.draw.line(screen, (70, int(70-i/HEIGHT*70), int(100-i/HEIGHT*70)), [0,i], [WIDTH, i], 2)

        # 푸리에/A-weighting 그래프 그리드
        # 세로선
        for draw_freq in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000]:
            pygame.draw.line(screen, (100, 100, 100), [draw_fft_x[draw_freq], GRAPH_FFT_Y], [draw_fft_x[draw_freq], GRAPH_FFT_Y+GRAPH_FFT_CY], 1)
        for i, draw_freq in zip(range(3, 8), [20, 100, 1000, 10000, 20000]):
            screen.blit(text[i], (draw_fft_x[draw_freq]-3, GRAPH_FFT_Y+GRAPH_FFT_CY+3))
        # 가로선
        for i in range(1, 4):
            pygame.draw.line(screen, (100, 100, 100), [GRAPH_FFT_X, GRAPH_FFT_Y + GRAPH_FFT_CY//4 * i], [GRAPH_FFT_X + GRAPH_FFT_CX, GRAPH_FFT_Y + GRAPH_FFT_CY//4 * i], 1)

        # 메인

        # 오디오 그래프
        pygame.draw.lines(screen, (200, 200, 200), False, list(zip(draw_audio_x, np.around(-audio_data*GRAPH_AUDIO_CY/2/max_head+GRAPH_AUDIO_Y+GRAPH_AUDIO_CY/2).astype(np.int16))), 1)
        # A-Weighting 그래프
        pygame.draw.lines(screen, (255, 127, 0), False, list(zip(draw_fft_x, np.around(-aweight_data*GRAPH_FFT_CY+GRAPH_FFT_Y+GRAPH_FFT_CY).astype(np.int16))), 1)
        # 푸리에변환 그래프
        pygame.draw.lines(screen, (200, 200, 200), False, list(zip(draw_fft_x, np.around(-fft_data*GRAPH_FFT_CY+GRAPH_FFT_Y+GRAPH_FFT_CY).astype(np.int16))), 1)
        # 피아노
        pxpos = 0
        for i in range(88):
            c = (max(0, int(np.round(piano_data[0][i]*400/max_head_norm))-200)+55, 200-abs(200-int(np.round(piano_data[0][i]*400/max_head_norm)))+55, max(0, 200-int(np.round(piano_data[0][i]*400/max_head_norm)))+55)
            if PIANO_TILE_TYPE[i] == 0:
                pygame.draw.rect(screen, c, [draw_piano_x[pxpos], GRAPH_PIANO_Y, draw_piano_x[pxpos+2]-draw_piano_x[pxpos]-1, int(np.round(GRAPH_PIANO_CY*2/3))], 0)
                pygame.draw.rect(screen, c, [draw_piano_x[pxpos], GRAPH_PIANO_Y+int(np.round(GRAPH_PIANO_CY*2/3)), draw_piano_x[pxpos+3]-draw_piano_x[pxpos]-1, int(np.round(GRAPH_PIANO_CY/3))], 0)
                pxpos += 2
            elif PIANO_TILE_TYPE[i] == 1:
                pygame.draw.rect(screen, c, [draw_piano_x[pxpos+1], GRAPH_PIANO_Y, draw_piano_x[pxpos+2]-draw_piano_x[pxpos+1]-1, int(np.round(GRAPH_PIANO_CY*2/3))], 0)
                pygame.draw.rect(screen, c, [draw_piano_x[pxpos], GRAPH_PIANO_Y+int(np.round(GRAPH_PIANO_CY*2/3)), draw_piano_x[pxpos+3]-draw_piano_x[pxpos]-1, int(np.round(GRAPH_PIANO_CY/3))], 0)
                pxpos += 2
            elif PIANO_TILE_TYPE[i] == 2:
                pygame.draw.rect(screen, c, [draw_piano_x[pxpos+1], GRAPH_PIANO_Y, draw_piano_x[pxpos+3]-draw_piano_x[pxpos+1]-1, int(np.round(GRAPH_PIANO_CY*2/3))], 0)
                pygame.draw.rect(screen, c, [draw_piano_x[pxpos], GRAPH_PIANO_Y+int(np.round(GRAPH_PIANO_CY*2/3)), draw_piano_x[pxpos+3]-draw_piano_x[pxpos]-1, int(np.round(GRAPH_PIANO_CY/3))], 0)
                pxpos += 3
            elif PIANO_TILE_TYPE[i] == 3:
                pygame.draw.rect(screen, c, [draw_piano_x[pxpos], GRAPH_PIANO_Y, draw_piano_x[pxpos+2]-draw_piano_x[pxpos]-1, int(np.round(GRAPH_PIANO_CY*2/3))-1], 0)
                pxpos += 1
            else:
                pygame.draw.rect(screen, c, [draw_piano_x[pxpos], GRAPH_PIANO_Y, int(np.round(GRAPH_PIANO_CX/52)), GRAPH_PIANO_CY], 0)

        # 그래프 틀 
        screen.blit(text[1], (GRAPH_AUDIO_X, GRAPH_AUDIO_Y - 35))
        pygame.draw.rect(screen, (255, 255, 255), [GRAPH_AUDIO_X, GRAPH_AUDIO_Y, GRAPH_AUDIO_CX, GRAPH_AUDIO_CY], 2)
        screen.blit(text[2], (GRAPH_FFT_X, GRAPH_FFT_Y - 35))
        pygame.draw.rect(screen, (255, 255, 255), [GRAPH_FFT_X, GRAPH_FFT_Y, GRAPH_FFT_CX, GRAPH_FFT_CY], 2)
        screen.blit(text[12], (GRAPH_PIANO_X, GRAPH_PIANO_Y - 35))

        # 푸리에변환 시작지점 마커
        pygame.draw.line(screen, (0, 255, 0), [GRAPH_AUDIO_X+int(np.round(GRAPH_AUDIO_CX*START_FRAME/CHUNK_DRAW)), GRAPH_AUDIO_Y-10], [GRAPH_AUDIO_X+int(np.round(GRAPH_AUDIO_CX*START_FRAME/CHUNK_DRAW)), GRAPH_AUDIO_Y+GRAPH_AUDIO_CY+10], 1)
        screen.blit(text[8], (GRAPH_AUDIO_X+int(np.round(GRAPH_AUDIO_CX*START_FRAME/CHUNK_DRAW))+5, GRAPH_AUDIO_Y+GRAPH_AUDIO_CY+4))
        # 푸리에변환 종료지점 마커
        pygame.draw.line(screen, (255, 0, 0), [GRAPH_AUDIO_X+int(np.round(GRAPH_AUDIO_CX*(START_FRAME+CHUNK_FFT)/CHUNK_DRAW)), GRAPH_AUDIO_Y-10], [GRAPH_AUDIO_X+int(np.round(GRAPH_AUDIO_CX*(START_FRAME+CHUNK_FFT)/CHUNK_DRAW)), GRAPH_AUDIO_Y+GRAPH_AUDIO_CY+10], 1)
        screen.blit(text[9], (GRAPH_AUDIO_X+int(np.round(GRAPH_AUDIO_CX*(START_FRAME+CHUNK_FFT)/CHUNK_DRAW))-58, GRAPH_AUDIO_Y-16))

        # 각주
        pygame.draw.line(screen, (200, 200, 200), [GRAPH_FFT_X + 10, GRAPH_FFT_Y + 10], [GRAPH_FFT_X + 15, GRAPH_FFT_Y + 10], 2)
        screen.blit(text[10], (GRAPH_FFT_X + 20, GRAPH_FFT_Y + 5))
        pygame.draw.line(screen, (255, 127, 0), [GRAPH_FFT_X + 10, GRAPH_FFT_Y + 20], [GRAPH_FFT_X + 15, GRAPH_FFT_Y + 20], 2)
        screen.blit(text[11], (GRAPH_FFT_X + 20, GRAPH_FFT_Y + 15))

    # 상태바
    pygame.draw.rect(screen, (10, 10, 10), [0, 0, WIDTH, 30], 0)
    mouse_temp = win32api.GetCursorPos()
    if win_x + WIDTH - 120 <= mouse_temp[0] <= win_x + WIDTH - 80 and win_y + 0 <= mouse_temp[1] <= win_y + 30 :
        pygame.draw.rect(screen, (100, 100, 100), [WIDTH - 120, 0, 40, 30], 0)        
    if win_x + WIDTH - 80 <= mouse_temp[0] <= win_x + WIDTH - 40 and win_y + 0 <= mouse_temp[1] <= win_y + 30 :
        pygame.draw.rect(screen, (100, 100, 100), [WIDTH - 80, 0, 40, 30], 0)
    if win_x + WIDTH - 40 <= mouse_temp[0] <= win_x + WIDTH and win_y + 0 <= mouse_temp[1] <= win_y + 30 :
        pygame.draw.rect(screen, (255, 0, 0), [WIDTH - 40, 0, 40, 30], 0)
    
    if eventKey_capture:
        pygame.draw.polygon(screen, (255, 255, 255), [[WIDTH-102, 11], [WIDTH-96, 15], [WIDTH-102, 19]], 0) # play
        pygame.draw.aalines(screen, (255, 255, 255), True, [[WIDTH-103, 10], [WIDTH-95, 15], [WIDTH-103, 20]], True) # play
    else:
        pygame.draw.line(screen, (255, 255, 255), [WIDTH-103, 10], [WIDTH-103, 20], 3) # pause
        pygame.draw.line(screen, (255, 255, 255), [WIDTH-97, 10], [WIDTH-97, 20], 3) # pause
    pygame.draw.line(screen, (255, 255, 255), [WIDTH-65, 20], [WIDTH-55, 20], 1) # _
    pygame.draw.line(screen, (255, 255, 255), [WIDTH-25, 10], [WIDTH-15, 20], 1) # X
    pygame.draw.line(screen, (255, 255, 255), [WIDTH-25, 20], [WIDTH-15, 10], 1) # X
    screen.blit(text[0], (15, 5))

    # 프레임 완성    
    pygame.display.update()
