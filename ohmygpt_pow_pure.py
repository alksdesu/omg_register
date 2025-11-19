"""
OhMyGPT PoW 求解器 - 纯 Python 实现

完整实现 Cap.js 流程:
1. GET /challenge 获取 challenge token 和配置
2. 计算 20 个 solutions (nonce)
3. POST /redeem 获取最终 powt token
"""

import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional, Dict
import time


class CapJSPoWSolver:
    """Cap.js Proof of Work 完整实现"""

    def __init__(self, api_endpoint: str = "https://cpjs.ohmycdn.com/97dabfa133/"):
        """
        初始化

        Args:
            api_endpoint: Cap.js API 端点
        """
        self.api_endpoint = api_endpoint.rstrip('/') + '/'
        self.challenge_url = self.api_endpoint + 'challenge'
        self.redeem_url = self.api_endpoint + 'redeem'

    @staticmethod
    def prng(seed: str, length: int) -> str:
        """
        伪随机数生成器 (FNV-1a + Xorshift)

        Args:
            seed: 种子字符串
            length: 生成长度

        Returns:
            十六进制字符串
        """
        # FNV-1a hash
        hash_val = 2166136261
        for char in seed:
            hash_val ^= ord(char)
            hash_val += (hash_val << 1) + (hash_val << 4) + (hash_val << 7) + \
                        (hash_val << 8) + (hash_val << 24)
            hash_val &= 0xFFFFFFFF

        state = hash_val
        result = ''

        def xorshift():
            nonlocal state
            state ^= (state << 13) & 0xFFFFFFFF
            state ^= state >> 17
            state ^= (state << 5) & 0xFFFFFFFF
            return state

        while len(result) < length:
            rnd = xorshift()
            result += format(rnd, '08x')

        return result[:length]

    @staticmethod
    def solve_single_challenge(salt: str, target: str, max_iterations: int = 10000000) -> Optional[int]:
        """
        求解单个 PoW challenge

        Args:
            salt: 盐值 (hex)
            target: 目标前缀 (hex)
            max_iterations: 最大尝试次数

        Returns:
            nonce 或 None
        """
        salt_bytes = salt.encode('utf-8')

        if len(target) % 2 != 0:
            target += '0'
        target_bytes = bytes.fromhex(target)
        target_bits = len(target) * 4

        full_bytes = target_bits // 8
        remaining_bits = target_bits % 8

        for nonce in range(max_iterations):
            nonce_str = str(nonce)
            nonce_bytes = nonce_str.encode('utf-8')

            hasher = hashlib.sha256()
            hasher.update(salt_bytes)
            hasher.update(nonce_bytes)
            hash_result = hasher.digest()

            if hash_result[:full_bytes] == target_bytes[:full_bytes]:
                if remaining_bits > 0 and full_bytes < len(target_bytes):
                    mask = 0xFF << (8 - remaining_bits)
                    if (hash_result[full_bytes] & mask) == (target_bytes[full_bytes] & mask):
                        return nonce
                else:
                    return nonce

        return None

    def generate_challenges(self, challenge_token: str, c: int, s: int, d: int) -> List[Tuple[str, str]]:
        """
        生成 challenges

        Args:
            challenge_token: 服务器 token
            c: challenge 数量
            s: salt 长度
            d: difficulty

        Returns:
            [(salt, target), ...] 列表
        """
        challenges = []
        for i in range(1, c + 1):
            salt = self.prng(f"{challenge_token}{i}", s)
            target = self.prng(f"{challenge_token}{i}d", d)
            challenges.append((salt, target))
        return challenges

    def solve_challenges(self, challenges: List[Tuple[str, str]], workers: int = 4,
                        max_iterations: int = 10000000, progress_callback=None) -> List[int]:
        """
        并行求解所有 challenges

        Args:
            challenges: [(salt, target), ...] 列表
            workers: 线程数
            max_iterations: 最大尝试次数
            progress_callback: 进度回调 (current, total)

        Returns:
            nonce 列表
        """
        results = [None] * len(challenges)
        completed = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_index = {
                executor.submit(self.solve_single_challenge, salt, target, max_iterations): i
                for i, (salt, target) in enumerate(challenges)
            }

            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    nonce = future.result()
                    if nonce is None:
                        raise Exception(f"Failed to solve challenge #{index}")
                    results[index] = nonce
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, len(challenges))

                except Exception as e:
                    print(f"[PoW] Error solving challenge #{index}: {e}")
                    raise

        return results

    def get_challenge(self) -> Dict:
        """
        获取 challenge

        Returns:
            {challenge: {c, s, d}, token, expires}
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Origin': 'https://www.ohmygpt.com',
                'Referer': 'https://www.ohmygpt.com/',
                'Content-Type': 'application/json'
            }
            # 注意: challenge 端点使用 POST 而不是 GET!
            response = requests.post(self.challenge_url, json={}, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get challenge: {e}")

    def redeem_token(self, challenge_token: str, solutions: List[int]) -> Dict:
        """
        兑换最终 token

        Args:
            challenge_token: challenge token
            solutions: nonce 数组

        Returns:
            {success, token, expires}
        """
        try:
            payload = {
                "token": challenge_token,
                "solutions": solutions
            }
            response = requests.post(
                self.redeem_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to redeem token: {e}")

    def solve(self, workers: int = 4, progress_callback=None) -> str:
        """
        完整的 PoW 求解流程

        Args:
            workers: 并行线程数
            progress_callback: 进度回调

        Returns:
            powt token 字符串
        """
        print("[PoW] 开始 Cap.js PoW 求解...")
        total_start = time.time()

        # 步骤1: 获取 challenge
        print("[PoW] 步骤1: 获取 challenge...")
        challenge_data = self.get_challenge()

        challenge_token = challenge_data['token']
        c = challenge_data['challenge']['c']
        s = challenge_data['challenge']['s']
        d = challenge_data['challenge']['d']

        print(f"[PoW]   Token: {challenge_token[:30]}...")
        print(f"[PoW]   Config: c={c}, s={s}, d={d}")

        # 步骤2: 生成 challenges
        print(f"[PoW] 步骤2: 生成 {c} 个 challenges...")
        challenges = self.generate_challenges(challenge_token, c, s, d)

        # 步骤3: 求解
        print(f"[PoW] 步骤3: 并行求解 (workers={workers})...")
        solve_start = time.time()

        solutions = self.solve_challenges(
            challenges,
            workers=workers,
            progress_callback=lambda cur, tot: print(f"[PoW]   进度: {cur}/{tot} ({cur*100//tot}%)")
        )

        solve_elapsed = time.time() - solve_start
        print(f"[PoW]   ✅ 求解完成! 耗时: {solve_elapsed:.2f}秒")
        print(f"[PoW]   Solutions: {solutions[:3]}... (共{len(solutions)}个)")

        # 步骤4: Redeem
        print("[PoW] 步骤4: Redeem token...")
        redeem_data = self.redeem_token(challenge_token, solutions)

        if not redeem_data.get('success'):
            raise Exception("Redeem failed")

        powt = redeem_data['token']
        total_elapsed = time.time() - total_start

        print(f"[PoW] ✅ 完成! 总耗时: {total_elapsed:.2f}秒")
        print(f"[PoW] PoWT Token: {powt}")

        return powt


def get_powt(workers: int = 4) -> str:
    """
    简化的获取 powt 函数

    Args:
        workers: 并行线程数

    Returns:
        powt token
    """
    solver = CapJSPoWSolver()
    return solver.solve(workers=workers)


if __name__ == "__main__":
    print("=== OhMyGPT PoW 纯 Python 求解器 ===\n")

    try:
        powt = get_powt(workers=4)
        print(f"\n✅ 成功获取 PoWT: {powt}")

    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
