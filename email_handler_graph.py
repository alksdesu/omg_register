"""使用 Microsoft Graph API 读取 Outlook 邮件"""

import requests
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

class OutlookGraphEmailHandler:
    """使用 Graph API 处理 Outlook 邮箱"""

    def __init__(self, email: str, client_id: str, refresh_token: str):
        self.email = email
        self.client_id = client_id
        self.refresh_token = refresh_token
        self.access_token = None

    def get_access_token(self) -> str:
        """获取 Access Token"""
        res = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": self.client_id,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "scope": "https://graph.microsoft.com/.default"
            }
        )

        if res.status_code != 200:
            raise Exception(f"获取 Access Token 失败: {res.text}")

        self.access_token = res.json()["access_token"]
        return self.access_token

    def get_messages(self, folder: str = "inbox", top: int = 50) -> list:
        """
        获取邮件列表

        Args:
            folder: 文件夹名称 (inbox, sentItems, drafts等)
            top: 返回数量
        """
        if not self.access_token:
            self.get_access_token()

        res = requests.get(
            f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={"$top": top}
        )

        if res.status_code != 200:
            raise Exception(f"获取邮件失败 (状态码 {res.status_code}): {res.text}")

        return res.json().get("value", [])

    def get_messages_from_multiple_folders(self, folders: list = None, top: int = 50) -> list:
        """
        从多个文件夹获取邮件

        Args:
            folders: 文件夹名称列表，默认检查 inbox 和 junkemail
            top: 每个文件夹返回的邮件数量

        Returns:
            所有文件夹的邮件列表
        """
        if folders is None:
            folders = ["inbox", "junkemail"]

        all_messages = []
        for folder in folders:
            try:
                messages = self.get_messages(folder=folder, top=top)
                all_messages.extend(messages)
            except Exception as e:
                # 某些文件夹可能不存在，忽略错误继续
                pass

        return all_messages

    def search_verification_email(
        self,
        sender: str,
        subject_keywords: list,
        timeout: int = 300,
        check_interval: int = 5
    ) -> Optional[Dict]:
        """
        搜索验证邮件

        Args:
            sender: 发件人邮箱或域名
            subject_keywords: 主题关键词列表
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）

        Returns:
            找到的邮件，包含 subject, from, body_preview, body_html 等字段
        """
        print(f"正在监听验证邮件...")
        print(f"  发件人: {sender}")
        print(f"  主题关键词: {subject_keywords}")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                messages = self.get_messages(top=20)

                for msg in messages:
                    from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '')
                    subject = msg.get('subject', '')
                    received_time = msg.get('receivedDateTime', '')

                    # 检查发件人
                    if sender and sender.lower() not in from_addr.lower():
                        continue

                    # 检查主题关键词
                    if subject_keywords:
                        if not any(kw.lower() in subject.lower() for kw in subject_keywords):
                            continue

                    # 检查时间（只看最近10分钟的邮件）
                    try:
                        msg_time = datetime.fromisoformat(received_time.replace('Z', '+00:00'))
                        if datetime.now(msg_time.tzinfo) - msg_time > timedelta(minutes=10):
                            continue
                    except:
                        pass

                    # 找到了！
                    print(f"\n✅ 找到验证邮件！")
                    print(f"  主题: {subject}")
                    print(f"  发件人: {from_addr}")
                    print(f"  时间: {received_time}")

                    return {
                        'id': msg.get('id'),
                        'subject': subject,
                        'from': from_addr,
                        'received_time': received_time,
                        'body_preview': msg.get('bodyPreview', ''),
                        'body_html': msg.get('body', {}).get('content', ''),
                        'body_type': msg.get('body', {}).get('contentType', ''),
                    }

                # 没找到，等待后重试
                elapsed = int(time.time() - start_time)
                print(f"  未找到，已等待 {elapsed}秒，继续检查...", end='\r')
                time.sleep(check_interval)

            except Exception as e:
                print(f"\n⚠️ 检查邮件时出错: {e}")
                time.sleep(check_interval)

        print(f"\n❌ 超时，未找到验证邮件")
        return None

    def extract_verification_link(self, email_data: Dict) -> Optional[str]:
        """从邮件中提取验证链接"""
        import re

        # 先尝试从HTML body提取
        body_html = email_data.get('body_html', '')
        body_preview = email_data.get('body_preview', '')

        # 常见验证链接模式
        patterns = [
            r'https://www\.ohmygpt\.com/[^\s"<>]+',
            r'https://ohmygpt\.com/[^\s"<>]+',
            r'http[s]?://[^\s"<>]+verify[^\s"<>]*',
        ]

        for pattern in patterns:
            # 先从HTML提取
            matches = re.findall(pattern, body_html)
            if matches:
                return matches[0]

            # 再从preview提取
            matches = re.findall(pattern, body_preview)
            if matches:
                return matches[0]

        return None


def test_graph_email():
    """测试 Graph API 邮件读取"""
    # 从文件读取账号
    with open("E:/SillyTavern/mail/ohmygpt/宝贝信息-268251119225449793.txt", 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()

    parts = first_line.split('----')
    email = parts[0]
    client_id = parts[2]
    refresh_token = parts[3]

    print(f"测试账号: {email}")
    print()

    handler = OutlookGraphEmailHandler(email, client_id, refresh_token)

    # 获取token
    print("[1] 获取 Access Token...")
    try:
        token = handler.get_access_token()
        print(f"✅ Token: {token[:50]}...")
    except Exception as e:
        print(f"❌ 失败: {e}")
        return

    # 获取收件箱
    print("\n[2] 获取收件箱邮件...")
    try:
        messages = handler.get_messages(top=5)
        print(f"✅ 找到 {len(messages)} 封邮件")

        for i, msg in enumerate(messages[:3], 1):
            subject = msg.get('subject', '(无主题)')
            from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '(未知)')
            preview = msg.get('bodyPreview', '')[:100]

            print(f"\n邮件 {i}:")
            print(f"  主题: {subject}")
            print(f"  发件人: {from_addr}")
            print(f"  预览: {preview}...")

        print("\n" + "="*70)
        print("✅✅✅ Graph API 完全正常工作！")
        print("="*70)

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_graph_email()
