"""
OhMyGPT 批量自动注册
支持配置文件自定义设置
"""

import sys
import time
import re
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

from email_handler_graph import OutlookGraphEmailHandler


def log(msg, verbose=True):
    """条件输出日志"""
    if verbose:
        print(msg)
        sys.stdout.flush()


def load_config(config_file="config.json"):
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log(f"⚠️  配置文件 {config_file} 不存在，使用默认配置")
        return {
            "referral_url": "https://www.ohmygpt.com/i/BG5E3MAB",
            "account_file": "宝贝信息-954251120002437504.txt",
            "headless": False,
            "max_accounts": None,
            "delay_between_accounts": 5
        }


def register_single_account(
    outlook_account_line: str,
    referral_url: str,
    headless: bool = True,
    verbose: bool = True
) -> dict:
    """
    注册单个账号

    Args:
        outlook_account_line: Outlook账号 (格式: email----password----client_id----refresh_token)
        referral_url: 邀请链接
        headless: 是否无头模式
        verbose: 是否详细输出（无头模式下强制为True）

    Returns:
        注册结果字典
    """
    # 无头模式下强制详细输出
    if headless:
        verbose = True

    parts = outlook_account_line.strip().split('----')
    if len(parts) != 4:
        return {"success": False, "error": "账号格式错误"}

    email, password, client_id, refresh_token = parts

    log("="*70, verbose)
    log(f"开始注册: {email}", verbose)
    log("="*70, verbose)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
           viewport={'width': 1920, 'height': 1080}
)

            # ========== 步骤1: 访问邀请码注册页面 ==========
            log(f"\n[1/6] 访问邀请页面: {referral_url}", verbose)
            page = context.new_page()

            start_time = time.time()
            page.goto(referral_url, wait_until="domcontentloaded", timeout=60000)
            load_time = time.time() - start_time

            log(f"  页面加载完成 ({load_time:.1f}秒)", verbose)
            log(f"  当前URL: {page.url}", verbose)

            # ========== 步骤2: 勾选四个框并继续 ==========
            log(f"\n[2/6] 勾选条款...", verbose)

            try:
                # 等待复选框完全加载（增加等待时间）
                log(f"  等待页面元素加载...", verbose)
                page.wait_for_selector('button[role="checkbox"]', timeout=15000)
                time.sleep(4)  # 额外等待确保页面完全渲染

                checkboxes = page.locator('button[role="checkbox"]').all()
                log(f"  找到 {len(checkboxes)} 个复选框", verbose)

                # 勾选所有checkbox（每个之间有延迟）
                for i, checkbox in enumerate(checkboxes):
                    checked_state = checkbox.get_attribute('aria-checked')
                    log(f"  第 {i+1} 个复选框状态: {checked_state}", verbose)
                    if checked_state == 'false':
                        checkbox.click()
                        time.sleep(0.3)  # 每次点击后等待
                        log(f"  ✅ 已勾选第 {i+1} 个", verbose)

                time.sleep(1.5)  # 等待按钮状态更新

                # 等待并点击"Understood"按钮
                try:
                    page.wait_for_selector('button:has-text("Understood"):not([disabled])', timeout=3000)
                    page.click('button:has-text("Understood")')
                    log(f"  ✅ 已点击'Understood'", verbose)
                except:
                    log(f"  ⚠️  'Understood'按钮仍未可用，尝试强制点击", verbose)
                    if page.locator('button:has-text("Understood")').count() > 0:
                        page.click('button:has-text("Understood")', force=True)
                        log(f"  ✅ 已强制点击'Understood'", verbose)

                time.sleep(2)

            except Exception as e:
                log(f"  ⚠️  勾选复选框时出错: {e}", verbose)

            # ========== 步骤3: 输入邮箱并发送验证邮件 ==========
            log(f"\n[3/6] 输入邮箱: {email}", verbose)

            try:
                # 查找并填写邮箱
                page.fill('input[type="email"]', email)
                log(f"  ✅ 已输入邮箱", verbose)

                # 等待"继续"按钮变为可点击
                log(f"  等待邮箱验证...", verbose)
                page.wait_for_selector('button.w-full:has-text("Continue"):not([disabled])', timeout=15000)

                email_sent_time = time.time()
                page.click('button.w-full:has-text("Continue")')
                log(f"  ✅ 已发送验证邮件", verbose)
                time.sleep(3)

                # ========== 读取等待验证页面上的安全验证码 ==========
                security_code = None
                try:
                    # 检查页面是否显示"安全答案"
                    if page.locator('text=Security Answer').count() > 0 or page.locator('text=安全验证').count() > 0:
                        log(f"  🔐 检测到安全验证提示", verbose)

                        # 查找显示安全验证码的圆形div
                        code_divs = page.locator('div.rounded-full').all()
                        for div in code_divs:
                            try:
                                text = div.inner_text().strip()
                                # 匹配格式如 A1, B6, C8
                                if re.match(r'^[A-Z]\d$', text):
                                    security_code = text
                                    log(f"  🔐 从等待页面读取到安全验证码: {security_code}", verbose)
                                    break
                            except:
                                continue
                except Exception as e:
                    log(f"  ℹ️  读取安全验证码时出错（可能没有安全验证）: {e}", verbose)

            except Exception as e:
                browser.close()
                return {"success": False, "error": f"发送验证邮件失败: {e}"}

            # ========== 步骤4: 等待并读取验证邮件 (20秒超时) ==========
            log(f"\n[4/6] 等待验证邮件 (检查 inbox 和 junkemail)...", verbose)

            email_handler = OutlookGraphEmailHandler(email, client_id, refresh_token)
            email_handler.get_access_token()

            verification_email = None
            max_wait_time = 20  # 最大等待20秒
            check_interval = 3  # 每3秒检查一次

            for i in range(int(max_wait_time / check_interval)):
                try:
                    # 从多个文件夹获取邮件
                    messages = email_handler.get_messages_from_multiple_folders(
                        folders=["inbox", "junkemail"],
                        top=5
                    )

                    for msg in messages:
                        from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '')
                        if 'dogeworks.com' not in from_addr.lower():
                            continue

                        subject = msg.get('subject', '')
                        if 'OhMyGPT' not in subject:
                            continue

                        received_time = msg.get('receivedDateTime', '')
                        try:
                            msg_time = datetime.fromisoformat(received_time.replace('Z', '+00:00'))
                            if msg_time.timestamp() >= email_sent_time - 1:
                                wait_time = time.time() - email_sent_time
                                log(f"  ✅ 收到邮件 ({wait_time:.1f}秒)", verbose)
                                verification_email = msg
                                break
                        except:
                            pass

                    if verification_email:
                        break

                    elapsed = (i + 1) * check_interval
                    log(f"  等待中... {elapsed}s / {max_wait_time}s", verbose)
                    time.sleep(check_interval)

                except Exception as e:
                    if verbose:
                        log(f"  检查邮件出错: {e}", verbose)
                    time.sleep(check_interval)

            if not verification_email:
                log(f"  ⚠️  超过 {max_wait_time} 秒未收到验证邮件，关闭浏览器准备重试", verbose)
                browser.close()
                return {"success": False, "error": "超时未收到验证邮件", "should_retry": True}

            # ========== 步骤5: 提取并在新标签页打开 magic link ==========
            log(f"\n[5/6] 提取magic link...", verbose)

            body_html = verification_email.get('body', {}).get('content', '')
            match = re.search(r'https://verified\.ohmycdn\.com/auth/v1/magic-link/[^\s"<>]+', body_html)

            if not match:
                browser.close()
                return {"success": False, "error": "未找到magic link"}

            magic_link = match.group(0)
            if verbose:
                log(f"  Magic link: {magic_link[:60]}...", verbose)

            # 在新标签页打开magic link
            log(f"\n[6/6] 打开magic link并授权...", verbose)
            magic_page = context.new_page()
            magic_page.goto(magic_link, wait_until="domcontentloaded", timeout=30000)
            time.sleep(1)

            # 检查是否有安全验证（Security Verification）
            try:
                # 检查页面是否包含 "Security Verification"
                if magic_page.locator('text=Security Verification').count() > 0:
                    log(f"  🔐 检测到安全验证页面", verbose)

                    if security_code:
                        log(f"  🔐 尝试点击安全选项: {security_code}", verbose)
                        # 查找并点击对应的安全选项（如 A1, B6, C8）
                        try:
                            # 等待选项加载
                            magic_page.wait_for_selector('input[type="radio"][name="answer"]', timeout=5000)
                            time.sleep(1)

                            # 使用aria-label查找对应的label并点击
                            clicked = False
                            try:
                                # 方法1: 通过aria-label精确匹配
                                label_selector = f'label:has(input[aria-label="Security option {security_code}"])'
                                if magic_page.locator(label_selector).count() > 0:
                                    magic_page.click(label_selector)
                                    log(f"  ✅ 已点击安全选项: {security_code}", verbose)
                                    clicked = True
                                    time.sleep(1)
                            except:
                                pass

                            # 方法2: 通过value查找input再点击父label
                            if not clicked:
                                try:
                                    input_selector = f'input[type="radio"][value="{security_code}"]'
                                    if magic_page.locator(input_selector).count() > 0:
                                        # 点击包含该input的label
                                        label_selector = f'label:has(input[value="{security_code}"])'
                                        magic_page.click(label_selector)
                                        log(f"  ✅ 已点击安全选项: {security_code} (方法2)", verbose)
                                        clicked = True
                                        time.sleep(1)
                                except:
                                    pass

                            # 方法3: 遍历所有label查找包含安全码的文本
                            if not clicked:
                                try:
                                    labels = magic_page.locator('label').all()
                                    log(f"  找到 {len(labels)} 个选项，遍历查找...", verbose)

                                    for label in labels:
                                        try:
                                            text = label.inner_text().strip()
                                            if text == security_code:
                                                label.click()
                                                log(f"  ✅ 已点击安全选项: {security_code} (方法3)", verbose)
                                                clicked = True
                                                time.sleep(1)
                                                break
                                        except:
                                            continue
                                except:
                                    pass

                            if not clicked:
                                log(f"  ⚠️  未找到匹配的安全选项: {security_code}", verbose)

                        except Exception as e:
                            log(f"  ⚠️  处理安全验证失败: {e}", verbose)
                    else:
                        log(f"  ⚠️  未从邮件中提取到安全验证码，可能需要手动处理", verbose)
            except Exception as e:
                log(f"  ℹ️  未检测到安全验证或检测出错: {e}", verbose)

            # 点击 "Approve Login" 按钮
            try:
                magic_page.wait_for_selector('button:has-text("Approve Login")', timeout=5000)
                magic_page.click('button:has-text("Approve Login")')
                log(f"  ✅ 已点击'Approve Login'", verbose)
            except Exception as e:
                log(f"  ⚠️  点击按钮时出错: {e}", verbose)

            # ========== 等待5秒后直接关闭 ==========
            log(f"\n[完成] 等待5秒后关闭浏览器...", verbose)
            time.sleep(5)

            # 关闭浏览器
            browser.close()

            log(f"\n{'='*70}", verbose)
            log(f"✅ 注册成功: {email}", verbose)
            log(f"{'='*70}", verbose)
            return {
                "success": True,
                "email": email,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    except Exception as e:
        log(f"\n❌ 注册失败: {e}", verbose)
        if verbose:
            import traceback
            traceback.print_exc()
        return {"success": False, "error": str(e)}


def batch_register(config_file="config.json"):
    """批量注册"""

    # 加载配置
    config = load_config(config_file)

    referral_url = config.get("referral_url")
    account_file = config.get("account_file")
    headless = config.get("headless", False)
    max_accounts = config.get("max_accounts")
    delay = config.get("delay_between_accounts", 5)

    # 从URL提取邀请码
    referral_code = referral_url.split('/')[-1] if '/' in referral_url else "未知"

    log("="*70)
    log("OhMyGPT 批量自动注册")
    log("="*70)
    log(f"邀请链接: {referral_url}")
    log(f"邀请码: {referral_code}")
    log(f"账号文件: {account_file}")
    log(f"无头模式: {headless}")
    if max_accounts:
        log(f"最大注册数: {max_accounts}")
    log("")

    # 读取账号
    try:
        with open(account_file, 'r', encoding='utf-8') as f:
            accounts = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        log(f"❌ 账号文件 {account_file} 不存在")
        return

    if max_accounts:
        accounts = accounts[:max_accounts]

    log(f"共 {len(accounts)} 个账号待注册\n")

    results = {"success": [], "failed": []}
    start_time = time.time()

    for i, account_line in enumerate(accounts, 1):
        log(f"\n{'='*70}")
        log(f"进度: {i}/{len(accounts)}")
        log(f"{'='*70}")

        # 最多重试3次
        max_retries = 3
        success = False

        for retry in range(max_retries):
            if retry > 0:
                log(f"\n🔄 第 {retry + 1} 次尝试...")

            result = register_single_account(
                account_line,
                referral_url=referral_url,
                headless=headless,
                verbose=True
            )

            if result.get('success'):
                results["success"].append({
                    "email": result.get('email'),
                    "timestamp": result.get('timestamp')
                })
                log(f"\n✅ 第 {i} 个账号注册成功!")
                success = True
                break
            else:
                # 如果是超时错误且标记为应该重试，则继续重试
                if result.get('should_retry') and retry < max_retries - 1:
                    log(f"\n⚠️  超时未收到邮件，{delay}秒后重试...")
                    time.sleep(delay)
                    continue
                else:
                    # 其他错误或已达最大重试次数
                    results["failed"].append({
                        "account": account_line.split('----')[0],
                        "error": result.get('error')
                    })
                    log(f"\n❌ 第 {i} 个账号注册失败: {result.get('error')}")
                    break

        # 延迟避免频率限制
        if i < len(accounts):
            log(f"\n等待 {delay} 秒后继续...")
            time.sleep(delay)

    # 总结
    total_time = time.time() - start_time

    log("\n" + "="*70)
    log("批量注册完成")
    log("="*70)
    log(f"总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
    log(f"成功: {len(results['success'])} 个")
    log(f"失败: {len(results['failed'])} 个")

    if results['success']:
        log(f"\n✅ 成功的账号:")
        for item in results['success']:
            log(f"  - {item['email']} ({item['timestamp']})")

    if results['failed']:
        log(f"\n❌ 失败的账号:")
        for item in results['failed']:
            log(f"  - {item['account']}: {item['error']}")

    # 保存结果
    output_file = f"registration_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    log(f"\n结果已保存到: {output_file}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='OhMyGPT 批量自动注册')
    parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')

    args = parser.parse_args()

    batch_register(args.config)
