import time
import re

def load_words(file_path):
    """
    사전 파일을 읽어 단어들을 set으로 반환합니다.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            words = {line.strip() for line in f}
        return words
    except FileNotFoundError:
        print(f"오류: 사전 파일을 찾을 수 없습니다: {file_path}")
        return None

def check_text(text, word_set):
    """
    입력된 텍스트에서 철자가 틀린 단어 목록을 찾아 반환합니다.
    """
    words_in_text = re.findall(r'\b[a-z]+\b', text.lower())
    misspelled_words = sorted(list(set(word for word in words_in_text if word not in word_set)))
    return misspelled_words

def levenshtein_distance(s1, s2):
    """
    두 단어 간의 레벤슈타인 거리를 계산합니다.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def get_suggestions(word, word_set, max_distance=2, limit=3):
    """
    오타에 대한 추천 단어 목록을 반환합니다.
    """
    suggestions = []
    for correct_word in word_set:
        # 단어 길이 차이가 max_distance보다 크면 계산하지 않음 (최적화)
        if abs(len(word) - len(correct_word)) > max_distance:
            continue
            
        dist = levenshtein_distance(word, correct_word)
        if dist <= max_distance:
            suggestions.append((correct_word, dist))
    
    # 거리가 짧은 순으로 정렬하고, 상위 limit 개수만큼 반환
    suggestions.sort(key=lambda x: x[1])
    return [s[0] for s in suggestions[:limit]]

def main():
    """
    메인 함수
    """
    dict_path = 'words.txt'
    
    print(f"사전 파일 '{dict_path}'을(를) 로드하는 중...")
    start_time = time.time()
    
    word_set = load_words(dict_path)
    
    end_time = time.time()
    
    if word_set:
        print(f"로드 완료! 총 {len(word_set):,}개의 단어를 로드했습니다.")
        print(f"로드 시간: {end_time - start_time:.2f}초\n")
        
        # 철자 검사 및 추천 테스트
        sample_text = "Thiss is a smaple text to check for misspelled wurds like 'zzxykw'."
        print(f"원본 텍스트: \"{sample_text}\"\n")
        
        misspelled = check_text(sample_text, word_set)
        
        if misspelled:
            print("발견된 오타 및 추천 단어:")
            for word in misspelled:
                suggestions = get_suggestions(word, word_set)
                print(f"- {word}: (추천: {', '.join(suggestions)})")
        else:
            print("텍스트에서 오타를 찾지 못했습니다.")

if __name__ == "__main__":
    main()
