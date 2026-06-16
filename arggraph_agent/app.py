#!/usr/bin/env python3
"""ArgGraph-Agent 命令行入口

用法：
    # 从文件读取
    python -m arggraph_agent.app --file samples/essay1.txt

    # 交互模式（粘贴文本）
    python -m arggraph_agent.app --interactive

    # 直接传入文本
    python -m arggraph_agent.app --text "坚持是一种美德……"

环境变量：
    DEEPSEEK_API_KEY=sk-xxxx  或  在 arggraph_agent/.env 文件中设置
"""

import sys
import os
import argparse

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arggraph_agent.agent import create_agent


def analyze_text(text: str, topic: str = None, verbose: bool = True):
    """分析议论文文本"""
    agent = create_agent()
    result = agent.analyze(text, essay_topic=topic, verbose=verbose)

    output = agent.format_output(result)
    print(output)

    # 保存结果到文件
    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    import json
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"result_{timestamp}.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 完整结果已保存到：{output_file}")

    return result


def analyze_file(filepath: str, topic: str = None):
    """从文件读取并分析"""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        print(f"错误：文件 {filepath} 为空")
        return

    print(f"📄 读取文件：{filepath}（{len(text)} 字）")
    analyze_text(text, topic=topic)


def interactive_mode():
    """交互模式：粘贴文本进行分析"""
    print("\n" + "=" * 60)
    print("ArgGraph-Agent 交互模式")
    print("=" * 60)
    print("请粘贴高考议论文文本，以单独一行的 'END' 结束：")
    print()

    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        except EOFError:
            break

    text = "\n".join(lines).strip()
    if not text:
        print("未输入文本，退出。")
        return

    topic = input("\n作文题目（可选，直接回车跳过）：").strip() or None

    analyze_text(text, topic=topic)


def demo_mode():
    """演示模式：使用内置范例（2019 上海高考真题，一类上 70 分）"""
    demo_essay = """记得歌里唱道："若非万种飞烟都过眼， 怎会迷恋巫山的那一片。"言甚是，若不曾含英咀华，怎能找到心中真正认同的美？而博览群书，知晓众人长，也必定会对自己的"根"，对心中的价值，拥有比别人更主动、更真诚的认同。

我们都是在比较之中，生发出对事物的感知与评判。王充的"两刃相割，利钝乃知，两论相驳，是非乃定"便是一例，通过比较，事物各自特点凸显，优劣立分，是非昌明。"比较"实在是我们认识事物的一把利器。

虽然"博闻"也不一定是比较，然而我向之所言，已带了主观的评判色彩，博闻本身使人丰富自我而并非无倾向，只是看到千万书卷，万种风烟之后，自我已悄然有了价值判断。"万种风烟之后"我之主体性方才显现，若是腹中空空，那么所谓认识与观点，自然基于空想，流于浅薄。

由是观之，我们要真正做到"博闻"才能真正客观地认识事物，所谓"操千曲而后晓声，观千剑而后识器"便是此意。在观"千剑"之后，形成对良器的判断，这便是博闻的作用了。

而所谓的博闻，与博闻中的比较，都需要一个开放的自我。否则会"井底之蛙"囿于身，失去了对外物的比较和借鉴，将会丢失自我的判断与认同。只有足够开阔的胸襟，执着的坚持，敢于突破，才能形成自身的认识。如冯友兰先生学贯中西，却终身致力于"阐旧邦以辅新命"，正是以为他在博采世界文化之众长后，更深刻地理解与认同了中国文化，他愿意投身于中国哲学史的浩海之中，以一己之力注解和发扬，若没有一个开放的自我，这是难以想象的。

万种风烟过眼后，有人得出"巫山之云最美"，便拒绝欣赏别处的美，我们大约都会觉得可惜、可叹。比较之后得到自己认同的价值，我们也不能抱守不放，而更要动态吸收，博采众长，才能算真正认识了事物。正如有人喜欢"中国味"音乐，而中国音乐也是文化交融、动态发展的，琵琶、扬琴、二胡……古时的异域风情，如今也成了正牌"民乐"，先人的灵活与进步，我们更应该守护与传扬。

正所谓，万种风烟过眼后，心中最美景，还是随时变，只是那份不变的，是根，是魂，是自我对它发自内心的认同。"""

    print("\n" + "=" * 60)
    print("ArgGraph-Agent 演示模式")
    print("=" * 60)
    print(f"内置范例：2019 年上海高考真题《万种风烟过眼后》")
    print(f"评分等级：一类上 70 分 | 共 {len(demo_essay)} 字")
    print()

    analyze_text(demo_essay, topic="万种风烟过眼后")


def main():
    parser = argparse.ArgumentParser(
        description="ArgGraph-Agent：高考议论文论证结构自动拆解智能体",
    )
    parser.add_argument(
        "--file", "-f", type=str,
        help="输入议论文文件路径",
    )
    parser.add_argument(
        "--text", "-t", type=str,
        help="直接传入议论文文本",
    )
    parser.add_argument(
        "--topic", type=str,
        help="作文题目（可选）",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="交互模式：粘贴文本进行分析",
    )
    parser.add_argument(
        "--demo", "-d", action="store_true",
        help="演示模式：使用内置范例",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="安静模式：不打印中间步骤",
    )

    args = parser.parse_args()
    verbose = not args.quiet

    if args.demo:
        demo_mode()
    elif args.interactive:
        interactive_mode()
    elif args.file:
        analyze_file(args.file, topic=args.topic)
    elif args.text:
        analyze_text(args.text, topic=args.topic)
    else:
        # 无参数时显示帮助，不再自动运行演示
        parser.print_help()
        print("\n💡 提示：使用 --demo 可快速体验，--text 直接传入文本，--file 从文件读取。")


if __name__ == "__main__":
    main()
