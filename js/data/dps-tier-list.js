/**
 * 团本 DPS 天梯（排名数据）
 *
 * 专精图标与职业信息统一见 specs.js，此处只保留层级与元数据。
 * 来源: https://www.wowhead.com/cn/guide/classes/tier-lists/dps-rankings-raids
 * 更新: 2026/10/26
 *
 * 由 tools/fetch_tier_lists.py 自动生成，请勿手改。
 */

const dpsTierList = {
  "title": "DPS Raid Rankings for Midnight Season 2 - Best Specs",
  "source": "Dratnos",
  "lastUpdated": "2026/10/26",
  "fetchedAt": "2026/10/26",
  "sourceUrl": "https://www.wowhead.com/cn/guide/classes/tier-lists/dps-rankings-raids",
  "tiers": {
    "S": {
      "name": "S",
      "description": "",
      "specs": []
    },
    "A+": {
      "name": "A+",
      "description": "",
      "specs": []
    },
    "A": {
      "name": "A",
      "description": "",
      "specs": [
        "warrior|武器",
        "druid|平衡",
        "priest|暗影",
        "mage|奥术",
        "warlock|恶魔学识",
        "hunter|射击",
        "rogue|奇袭",
        "monk|踏风"
      ]
    },
    "B": {
      "name": "B",
      "description": "",
      "specs": [
        "evoker|湮灭",
        "rogue|敏锐",
        "warlock|毁灭",
        "demon-hunter|浩劫",
        "demon-hunter|噬灭",
        "death-knight|冰霜",
        "shaman|元素",
        "death-knight|邪恶",
        "mage|冰霜",
        "warlock|痛苦",
        "shaman|增强",
        "evoker|增辉",
        "paladin|惩戒"
      ]
    },
    "C": {
      "name": "C",
      "description": "",
      "specs": [
        "hunter|野兽控制",
        "warrior|狂怒",
        "druid|野性",
        "rogue|狂徒",
        "mage|火焰",
        "hunter|生存"
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

export default dpsTierList;
