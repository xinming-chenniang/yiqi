/**
 * 大秘境 DPS 天梯（排名数据）
 *
 * 专精图标与职业信息统一见 specs.js，此处只保留层级与元数据。
 * 来源: https://www.wowhead.com/cn/guide/classes/tier-lists/dps-rankings-mythic-plus
 * 更新: 2026/10/26
 *
 * 由 tools/fetch_tier_lists.py 自动生成，请勿手改。
 */

const mplusDpsTierList = {
  "title": "Mythic+ DPS Rankings - Tier List for Midnight Season 2",
  "source": "Wowhead",
  "lastUpdated": "2026/10/26",
  "fetchedAt": "2026/10/26",
  "sourceUrl": "https://www.wowhead.com/cn/guide/classes/tier-lists/dps-rankings-mythic-plus",
  "tiers": {
    "S": {
      "name": "S",
      "description": "",
      "specs": [
        "rogue|敏锐"
      ]
    },
    "A+": {
      "name": "A+",
      "description": "",
      "specs": [
        "warlock|恶魔学识",
        "warrior|武器",
        "mage|奥术",
        "rogue|奇袭",
        "shaman|元素"
      ]
    },
    "A": {
      "name": "A",
      "description": "",
      "specs": [
        "death-knight|邪恶",
        "demon-hunter|噬灭",
        "rogue|狂徒",
        "monk|踏风",
        "paladin|惩戒",
        "druid|野性"
      ]
    },
    "B": {
      "name": "B",
      "description": "",
      "specs": [
        "warlock|毁灭",
        "druid|平衡",
        "death-knight|冰霜",
        "hunter|射击",
        "demon-hunter|浩劫",
        "shaman|增强",
        "hunter|生存",
        "evoker|湮灭",
        "hunter|野兽控制",
        "priest|暗影",
        "warrior|狂怒"
      ]
    },
    "C": {
      "name": "C",
      "description": "",
      "specs": [
        "mage|冰霜",
        "mage|火焰",
        "warlock|痛苦",
        "evoker|增辉"
      ]
    },
    "D": {
      "name": "D",
      "description": "",
      "specs": []
    },
    "F": {
      "name": "F",
      "description": "",
      "specs": []
    }
  }
};

export default mplusDpsTierList;
