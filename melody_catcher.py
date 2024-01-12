import numpy as np
import pygame
import time
import win32api
import win32gui

# 매개변수

TITLE = "Melody Catcher"

RATE = 44100
CHUNK = 1024 * 4

FPS = 60

WIDTH = 960
HEIGHT_STATE = 30
HEIGHT = HEIGHT_STATE + 540

FREQ_MASK = 25
FREQ_CUTOFF = 5000
FREQ_TUNE = np.array([27.5000 * 2 ** (i / 12) for i in range(88)])
ROLLOFF_START = 40
ROLLOFF_END = 200
NOISEFLOOR = 5

GRAPH_AUDIO_CY = 100
GRAPH_AUDIO_X = 20
GRAPH_AUDIO_Y = HEIGHT - GRAPH_AUDIO_CY - 30
GRAPH_AUDIO_CX = WIDTH - GRAPH_AUDIO_X * 2

GRAPH_FREQ_CY = 300
GRAPH_FREQ_X = 20
GRAPH_FREQ_Y = HEIGHT_STATE + 50
GRAPH_FREQ_CX = 350

GRAPH_PIANO_X = 400
GRAPH_PIANO_Y = 200

PEAK_HOLD = 1
PEAK_REALESE = 0.5
SMOOTH = 0.2

# 프로세스 레퍼런스
HWND = None

pygame.init()
pygame.display.set_caption(TITLE)
pygame.display.set_icon(pygame.image.load("img/icon_mc.png"))
clock = pygame.time.Clock()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)

# 텍스트 객체 사전 로딩
text = { "Melody_Catcher_title": pygame.font.Font("font/Pretendard-Regular.otf", 15).render("Melody Catcher", True,
                                                                                            (255, 255, 255)),
         "Audio_Signal": pygame.font.Font("font/Pretendard-Thin.otf", 25).render("Audio Signal", True, (255, 255, 255)),
         "Frequency": pygame.font.Font("font/Pretendard-Thin.otf", 25).render("Frequency", True, (255, 255, 255)),
         "Tune_Intensity": pygame.font.Font("font/Pretendard-Thin.otf", 25).render("Tune Intensity", True, (255, 255, 255)) }

mouseprepos = win32api.GetCursorPos()
mouse = win32api.GetCursorPos()
keyboardpre = pygame.key.get_pressed()
keyboard = pygame.key.get_pressed()

eventKey_capture = False
eventKey_disableWindow = False
eventKey_moveWindow = False
eventKey_quit = False

from audio_importer import audio_importer

importer = audio_importer(RATE, FPS, CHUNK)

draw_audio_x = [GRAPH_AUDIO_X + int(np.round(GRAPH_AUDIO_CX * i / CHUNK)) for i in range(CHUNK)]
draw_fft_x = [GRAPH_FREQ_X + int(np.round(np.log10(i + 1) / np.log10(FREQ_CUTOFF - FREQ_MASK) * GRAPH_FREQ_CX)) for i in
              range(FREQ_CUTOFF - FREQ_MASK)]
draw_tune_x = [GRAPH_FREQ_X + int(np.round(np.log10(i - FREQ_MASK) / np.log10(FREQ_CUTOFF - FREQ_MASK) * GRAPH_FREQ_CX)) for i in
               FREQ_TUNE]

hanning_window = [np.sin(x / (np.pi * CHUNK)) for x in range(CHUNK)]
tune_weight = [min(1, max(0, (f - ROLLOFF_START) / (ROLLOFF_END - ROLLOFF_START))) for f in FREQ_TUNE]

tune_data_list = np.array(
    [np.array([0] * 88, dtype=np.float64) for _ in range(int(np.round(SMOOTH * FPS)))])

peak = 1
peak_fresh = time.time()

pygame.display.flip()


# 프로세스 레퍼런스 업데이트
def callback(hwnd, extra):
    if win32gui.GetWindowText(hwnd) == TITLE:
        global HWND
        HWND = hwnd


win32gui.EnumWindows(callback, None)

win_x, win_y, _, _ = win32gui.GetWindowRect(HWND)

while not eventKey_quit:

    clock.tick(FPS)

    mouse = win32api.GetCursorPos()

    # 이벤트 검사
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            eventKey_quit = True

        # 키보드 이벤트
        elif event.type == pygame.KEYDOWN:
            keyboard = pygame.key.get_pressed()
            # ESC
            if keyboard[pygame.K_ESCAPE]:
                eventKey_quit = True
            # SPACEBAR
            if keyboard[pygame.K_SPACE] and not keyboardpre[pygame.K_SPACE]:
                eventKey_capture = not eventKey_capture

        elif event.type == pygame.KEYUP:
            keyboard = pygame.key.get_pressed()

        # 마우스 이벤트
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 창 이동
            if win_x <= mouse[0] <= win_x + WIDTH - 120 and win_y <= mouse[1] <= win_y + 30:
                eventKey_moveWindow = True

        elif event.type == pygame.MOUSEBUTTONUP:
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
        win32gui.SetWindowPos(HWND, 0, win_x + mouse[0] - mouseprepos[0], win_y + mouse[1] - mouseprepos[1], WIDTH,
                              HEIGHT, 64)
        win_x, win_y, _, _ = win32gui.GetWindowRect(HWND)

    # 이전 프레임 데이터 보관 처리
    keyboardpre = keyboard
    mouseprepos = mouse

    # 데이터 가공

    # 오디오 데이터 불러오기
    audio_data = importer.get_audio_data()

    # 헤드룸 조정
    peak_temp = max(abs(audio_data))
    if peak - NOISEFLOOR <= peak_temp <= peak:
        peak_fresh = time.time()
    elif peak < peak_temp:
        peak = peak_temp
        peak_fresh = time.time()
    elif time.time() - peak_fresh > PEAK_HOLD:
        peak = max(peak - peak / PEAK_REALESE / FPS, peak_temp)

    # 오디오 데이터 정규화
    audio_data = audio_data / peak

    # 푸리에 변환
    fft_data = np.abs(np.fft.fft(audio_data * hanning_window * 2, n=RATE, norm="ortho")[0: RATE // 2])

    # 음정 가중치 변환
    tune_data = np.interp(FREQ_TUNE, [i for i in range(RATE // 2)], fft_data) * tune_weight

    # 음정 가중치 데이터 저장
    tune_data_list = np.insert(tune_data_list[: -1], 0, tune_data, axis=0)

    # 현재 음정 데이터 계산
    data = tune_data_list.mean(axis=0)

    # 화면 구성
    if not eventKey_capture:

        # 배경
        for i in range(HEIGHT):
            pygame.draw.line(screen, (70, int(70 - i / HEIGHT * 70), int(100 - i / HEIGHT * 70)), [0, i], [WIDTH, i], 2)

        # 메인

        # 오디오 그래프
        pygame.draw.lines(screen, (200, 200, 200), False, list(zip(draw_audio_x, np.around(
            -audio_data * GRAPH_AUDIO_CY / 2 + GRAPH_AUDIO_Y + GRAPH_AUDIO_CY / 2).astype(np.int16))), 1)

        # 푸리에변환 그래프
        pygame.draw.lines(screen, (200, 200, 200), False,
                          list(zip(draw_fft_x,
                                   np.around(-fft_data[FREQ_MASK: FREQ_CUTOFF] * 100 + GRAPH_FREQ_CY).astype(np.int16))), 1)

        # 음정가중치 그래프
        pygame.draw.lines(screen, (0, 255, 0), False, list(
            zip(draw_tune_x, np.around(-data * 100 + GRAPH_FREQ_CY).astype(np.int16))), 2)

        # 피아노
        index = 0
        data_peak = max(np.max(data), 0.1)
        for i, x in enumerate([GRAPH_PIANO_X + 10 * i for i in range(52)]):
            # 흰 건반
            color = (max(0, int((data[index] - data_peak / 2) * 2 * 255 / data_peak)),
                     int((data_peak / 2 - abs(data_peak / 2 - data[index])) * 2 * 255 / data_peak),
                     max(0, int((data_peak / 2 - data[index]) * 2 * 255 / data_peak)))
            if i == 51:
                pygame.draw.rect(screen, color, [x, GRAPH_PIANO_Y, 8, 100], 0)
            elif i == 0 or i % 7 == 2 or i % 7 == 5:
                pygame.draw.polygon(screen, color, [[x, GRAPH_PIANO_Y], [x + 5, GRAPH_PIANO_Y], [x + 5, GRAPH_PIANO_Y + 60], [x + 8, GRAPH_PIANO_Y + 60], [x + 8, GRAPH_PIANO_Y + 100], [x, GRAPH_PIANO_Y + 100]], 0)
            elif i % 7 == 1 or i % 7 == 4:
                pygame.draw.polygon(screen, color, [[x + 3, GRAPH_PIANO_Y], [x + 8, GRAPH_PIANO_Y], [x + 8, GRAPH_PIANO_Y + 100], [x, GRAPH_PIANO_Y + 100], [x, GRAPH_PIANO_Y + 60], [x + 3, GRAPH_PIANO_Y + 60]], 0)
            else:
                pygame.draw.polygon(screen, color, [[x + 3, GRAPH_PIANO_Y], [x + 5, GRAPH_PIANO_Y], [x + 5, GRAPH_PIANO_Y + 60], [x + 8, GRAPH_PIANO_Y + 60], [x + 8, GRAPH_PIANO_Y + 100], [x, GRAPH_PIANO_Y + 100], [x, GRAPH_PIANO_Y + 60], [x + 3, GRAPH_PIANO_Y + 60]], 0)
            index += 1
            # 검은 건반
            if not (i == 51 or i % 7 == 1 or i % 7 == 4):
                color = (max(0, int((data[index] - data_peak / 2) * 2 * 255 / data_peak)),
                         int((data_peak / 2 - abs(data_peak / 2 - data[index])) * 2 * 255 / data_peak),
                         max(0, int((data_peak / 2 - data[index]) * 2 * 255 / data_peak)))
                pygame.draw.rect(screen, color, [x + 7, GRAPH_PIANO_Y, 5, 59], 0)
                index += 1

        # 그래프 틀
        screen.blit(text["Audio_Signal"], (GRAPH_AUDIO_X, GRAPH_AUDIO_Y - 35))
        pygame.draw.rect(screen, (255, 255, 255),
                         [GRAPH_AUDIO_X, GRAPH_AUDIO_Y, GRAPH_AUDIO_CX, GRAPH_AUDIO_CY], 3)
        screen.blit(text["Frequency"], (GRAPH_FREQ_X, GRAPH_FREQ_Y - 35))
        pygame.draw.rect(screen, (255, 255, 255), [GRAPH_FREQ_X, GRAPH_FREQ_Y, GRAPH_FREQ_CX, GRAPH_FREQ_CY], 3)
        screen.blit(text["Tune_Intensity"], (GRAPH_PIANO_X, GRAPH_PIANO_Y - 35))

    # 상태바
    pygame.draw.rect(screen, (10, 10, 10), [0, 0, WIDTH, 30], 0)
    mouse_temp = win32api.GetCursorPos()
    if win_x + WIDTH - 120 <= mouse_temp[0] <= win_x + WIDTH - 80 and win_y + 0 <= mouse_temp[1] <= win_y + 30:
        pygame.draw.rect(screen, (100, 100, 100), [WIDTH - 120, 0, 40, 30], 0)
    if win_x + WIDTH - 80 <= mouse_temp[0] <= win_x + WIDTH - 40 and win_y + 0 <= mouse_temp[1] <= win_y + 30:
        pygame.draw.rect(screen, (100, 100, 100), [WIDTH - 80, 0, 40, 30], 0)
    if win_x + WIDTH - 40 <= mouse_temp[0] <= win_x + WIDTH and win_y + 0 <= mouse_temp[1] <= win_y + 30:
        pygame.draw.rect(screen, (255, 0, 0), [WIDTH - 40, 0, 40, 30], 0)

    if eventKey_capture:
        pygame.draw.polygon(screen, (255, 255, 255), [[WIDTH - 102, 11], [WIDTH - 96, 15], [WIDTH - 102, 19]],
                            0)  # play
        pygame.draw.aalines(screen, (255, 255, 255), True, [[WIDTH - 103, 10], [WIDTH - 95, 15], [WIDTH - 103, 20]],
                            True)  # play
    else:
        pygame.draw.line(screen, (255, 255, 255), [WIDTH - 103, 10], [WIDTH - 103, 20], 3)  # pause
        pygame.draw.line(screen, (255, 255, 255), [WIDTH - 97, 10], [WIDTH - 97, 20], 3)  # pause
    pygame.draw.line(screen, (255, 255, 255), [WIDTH - 65, 20], [WIDTH - 55, 20], 1)  # _
    pygame.draw.line(screen, (255, 255, 255), [WIDTH - 25, 10], [WIDTH - 15, 20], 1)  # X
    pygame.draw.line(screen, (255, 255, 255), [WIDTH - 25, 20], [WIDTH - 15, 10], 1)  # X
    screen.blit(text["Melody_Catcher_title"], (15, 5))

    # 프레임 완성    
    pygame.display.update()
