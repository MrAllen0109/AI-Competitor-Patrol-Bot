import pandas as pd
import requests
import glob
import os
import json
import time
import re

# ================= 1. 配置区 (云端安全升级版) =================
# 使用 os.getenv() 读取环境变量，如果云端没配置，就使用后面的默认值（方便你本地继续测试）
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "3d895f555bd848648b86723aa54a857b") 
COZE_PAT = os.environ.get("COZE_PAT", "pat_da9Ns6FV8NCchUitLijXhv7r7cp2TzwCjolIV2kqZcDuDAlM904SHQgKFlm02tXb")
BOT_ID = "7614420724107100202" 
ENABLE_PUSHPLUS = True

# ================= 2. 读取本地 CSV 数据 =================
csv_files = glob.glob('./data/xhs/csv/search_comments_*.csv')
if not csv_files:
    print("❌ 没找到评论文件，请确认爬虫是否跑完！")
    exit()

latest_file = max(csv_files, key=os.path.getctime)
print(f"📁 正在读取最新情报文件: {latest_file}")

try:
    df = pd.read_csv(latest_file)
    comments = df['content'].head(20).tolist()
    text_content = " | ".join(comments)
    print("\n" + "=" * 40)
    print(f"👀 [面试官请看] 成功提取到 {len(comments)} 条真实评论数据：\n")
    print(text_content)
    print("=" * 40 + "\n")
except KeyError:
    print("❌ CSV 列名不匹配，请检查内容列是否为 'content'")
    exit()

# ================= 3. 调用 Coze V3 API =================
print("🤖 正在呼叫云端 AI 增长黑客进行分析...")
headers = {
    "Authorization": f"Bearer {COZE_PAT}",
    "Content-Type": "application/json"
}

coze_chat_url = "https://api.coze.cn/v3/chat"

payload = {
    "bot_id": BOT_ID,
    "user_id": "tester_shanghai_pm",
    "stream": False,
    "additional_messages": [
        {
            "role": "user", 
            "content": f"请立刻调用 Competitor_Crisis_Monitor 工作流分析以下反馈。你必须【原封不动】地输出工作流返回的 JSON！\n【绝对禁止】嵌套字典！【绝对禁止】输出英文格式！\n你必须 100% 严格包含以下第一层字段：target_competitor, crisis_level_stars, status, pain_point_analysis, strategic_direction, xiaohongshu_copy, pr_action。\n\n用户反馈：\n{text_content}", 
            "content_type": "text"
        }
    ]
}

chat_res = requests.post(coze_chat_url, headers=headers, json=payload).json()
if chat_res.get("code") != 0:
    print("❌ Coze API 握手失败:", chat_res)
    exit()

chat_id = chat_res["data"]["id"]
conversation_id = chat_res["data"]["conversation_id"]
print(f"⏳ 对话已建立 (ID: {chat_id})，等待大模型处理...")

retrieve_url = f"https://api.coze.cn/v3/chat/retrieve?chat_id={chat_id}&conversation_id={conversation_id}"
while True:
    status_res = requests.get(retrieve_url, headers=headers).json()
    if "data" not in status_res:
        print(f"\n❌ Coze API 轮询被拒绝！原始返回: {status_res}")
        exit()
    status = status_res["data"]["status"]
    if status == "completed":
        break
    elif status in ["failed", "canceled", "rejected", "requires_action"]:
        print(f"❌ 大模型处理异常中断，当前状态: {status}")
        exit()
    time.sleep(1.5)

msg_url = f"https://api.coze.cn/v3/chat/message/list?chat_id={chat_id}&conversation_id={conversation_id}"
msg_res = requests.get(msg_url, headers=headers).json()

bot_answer = ""
for msg in msg_res.get("data", []):
    if msg.get("type") == "answer":
        bot_answer = msg.get("content", "")
        break

print("\n📢 终端自检：大模型返回的原始数据：\n", bot_answer)

# ================= 4. 终极防弹 JSON 解析 + 智能净化引擎 =================
def flatten_to_text(data):
    """智能文本净化器：把大模型瞎嵌套的字典或列表，强行拍扁成人类能看懂的漂亮文本"""
    if isinstance(data, dict):
        return "\n".join([f"  - {str(v)}" for k, v in data.items()])
    elif isinstance(data, list):
        return "\n".join([f"  - {str(item)}" for item in data])
    else:
        return str(data)

try:
    clean_text = bot_answer.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    start_idx = clean_text.find('{')
    end_idx = clean_text.rfind('}')
    
    if start_idx == -1 or end_idx == -1:
        raise ValueError("大模型回复中未检测到完整的 {} 结构")
        
    json_str = clean_text[start_idx:end_idx+1]
    result_dict = json.loads(json_str)
    
    # 提取顶层字段并直接经过【智能净化器】处理
    target = flatten_to_text(result_dict.get("target_competitor", "大盘全局监控"))
    stars = flatten_to_text(result_dict.get("crisis_level_stars", "⭐️"))
    status_text = flatten_to_text(result_dict.get("status", "状态评估中..."))
    pain_point_text = flatten_to_text(result_dict.get("pain_point_analysis", "暂无深度痛点"))
    direction_text = flatten_to_text(result_dict.get("strategic_direction", "暂无动作"))
    xhs_copy = flatten_to_text(result_dict.get("xiaohongshu_copy", ""))
    pr_action = flatten_to_text(result_dict.get("pr_action", ""))

    wechat_msg = f"【星跃 AI 商业情报与风控决策系统】\n"
    wechat_msg += f"=================================\n"
    wechat_msg += f"🎯 锁定竞品：{target}\n"
    wechat_msg += f"🚨 预警星级：{stars}\n"
    wechat_msg += f"---------------------------------\n"
    wechat_msg += f"[📊 风险动态评估]\n"
    wechat_msg += f"• 态势定性：{status_text}\n"
    wechat_msg += f"• 痛点击穿：\n{pain_point_text}\n"
    wechat_msg += f"---------------------------------\n"
    wechat_msg += f"[⚔️ 营销决策指令]\n"
    wechat_msg += f"• 战略中枢：\n{direction_text}\n"
    
    if xhs_copy and xhs_copy.lower() not in ["null", "none", "", "暂无"]:
        wechat_msg += f"\n[📝 小红书截流 SOP]\n{xhs_copy}\n"
        
    if pr_action and pr_action.lower() not in ["null", "none", "", "暂无"]:
        wechat_msg += f"\n[📢 公关动作建议]\n{pr_action}\n"

    ai_analysis = wechat_msg

except json.JSONDecodeError as e:
    print(f"\n❌ JSON 解析致命错误: {e}")
    ai_analysis = f"⚠️ 系统解析异常，大模型格式完全损坏。原始返回：\n{bot_answer}"
except Exception as e:
    print(f"\n❌ 运行时异常: {e}")
    ai_analysis = f"⚠️ 系统运行异常：{e}"

print("-" * 30)
print(f"✅ 准备发给微信的内容是：\n{ai_analysis}")
print("-" * 30)

# ================= 5. 推送到你的微信 =================
if not ENABLE_PUSHPLUS:
    exit()

if len(ai_analysis) < 5:
    exit()

print("🚀 正在将 AI 简报发射到你的微信...")
url = 'http://www.pushplus.plus/send'
push_data = {
    "token": PUSHPLUS_TOKEN,
    "title": "🚨 AI 竞品舆情预警",
    "content": ai_analysis,
    "template": "txt"
}

response = requests.post(url, json=push_data)
res_json = response.json()
if res_json.get("code") == 200:
    print("✅ 真正发送成功！快看你的手机微信！")
else:
    print(f"❌ 发送失败，Pushplus 拦截原因：{res_json.get('msg', '未知错误')}")