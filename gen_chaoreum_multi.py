"""Generate multiple 차오름 LoKR songs with varied styles."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music

BEST_CKPT = r"C:\Users\leo\chaoreum_output\checkpoints\epoch_400_loss_0.9721"
SAVE_DIR = r"C:\Users\leo\chaoreum_samples\multi"

SONGS = [
    {
        "name": "01_신작로에서",
        "caption": "Korean trot, emotional male vocals, vibrato, slow ballad, string orchestra, piano, melancholic, 72 BPM",
        "lyrics": """[verse]
신작로 가로등 아래
빗물이 흘러내리고
우산도 없이 걷는 밤
그대 생각뿐이오

[chorus]
사랑아 어디로 갔나
이 가슴이 텅 비었구나
한 잔의 막걸리에도
그대 얼굴이 떠오르오

[verse]
시장통 어묵 한 꼬치
둘이서 나눠 먹던 날
이제는 혼자 앉아서
빈 의자를 바라보오"""
    },
    {
        "name": "02_막차타고",
        "caption": "Korean trot, upbeat male vocals, energetic, brass section, drum beat, cheerful trot, 128 BPM",
        "lyrics": """[verse]
오늘도 야근 끝나고
막차를 타고 달려가
시원한 맥주 한 잔에
세상 걱정 다 잊자

[chorus]
달려라 달려 막차야
내 청춘도 함께 달린다
내일 걱정은 내일 하고
오늘 밤은 신나게

[verse]
옆자리 아저씨도
고개를 끄덕끄덕
우리 모두 힘든 하루
웃으면서 이겨내자"""
    },
    {
        "name": "03_어머니",
        "caption": "Korean trot, emotional male vocals, deep vibrato, slow tempo, acoustic guitar, heartfelt ballad, 66 BPM",
        "lyrics": """[verse]
하얗게 센 머리카락
굽어진 그 허리에도
새벽마다 일어나
밥상을 차려주시네

[chorus]
어머니 어머니
그 사랑 어이 갚으리
주름진 두 손 잡으면
눈물이 하염없이

[verse]
전화기 너머로 들리는
괜찮다는 그 한마디
그 말이 더 아프게
이 가슴을 적시네

[chorus]
어머니 어머니
그 사랑 어이 갚으리
다음에 꼭 내려갈게
건강하게 계세요"""
    },
    {
        "name": "04_포장마차에서",
        "caption": "Korean trot, warm male vocals, medium tempo, accordion, folk guitar, nostalgic, sentimental, 88 BPM",
        "lyrics": """[verse]
골목길 끝자락에
빨간 천막 불빛 아래
소주잔을 기울이며
옛 친구를 떠올려

[chorus]
한 잔 두 잔 세 잔째
눈물이 술잔에 빠지네
그리운 사람들아
잘 살고 있는 거지

[verse]
라디오에서 흘러나온
옛날 그 노래에
어깨를 들썩이다가
코끝이 찡해지네"""
    },
    {
        "name": "05_항구의밤",
        "caption": "Korean trot, powerful male vocals, dramatic vibrato, electric guitar, synthesizer, sea breeze mood, 100 BPM",
        "lyrics": """[verse]
파도가 부서지는
이 항구의 밤거리에
갈매기 우는 소리
내 마음을 흔드네

[chorus]
떠나간 배는 돌아오는데
떠나간 사람은 왜 안 오나
기다림에 지친 이 밤
등대불만 켜져 있소

[verse]
짠내 나는 바닷바람
옷깃을 여미면서
수평선 너머로
그대를 부르오"""
    },
]

handler = AceStepHandler()
handler.initialize_service(
    project_root=r"C:\Users\leo\ace-step-v15",
    config_path=None,
    device="cuda",
    offload_to_cpu=False,
)

print(f"Loading LoKR: {BEST_CKPT}", flush=True)
handler.load_lora(BEST_CKPT)

for i, song in enumerate(SONGS):
    print(f"\n[{i+1}/{len(SONGS)}] {song['name']}", flush=True)
    save_path = os.path.join(SAVE_DIR, song["name"])
    os.makedirs(save_path, exist_ok=True)
    params = GenerationParams(
        caption=song["caption"],
        lyrics=song["lyrics"],
        instrumental=False,
        vocal_language="ko",
        duration=60,
        task_type="text2music",
        thinking=False,
    )
    config = GenerationConfig(
        batch_size=1,
        seeds=[42],
        audio_format="wav",
    )
    res = generate_music(
        dit_handler=handler,
        llm_handler=None,
        params=params,
        config=config,
        save_dir=save_path,
    )
    for audio in res.audios:
        print(f"  -> {audio.get('path','saved')}", flush=True)

print("\nALL DONE!", flush=True)
