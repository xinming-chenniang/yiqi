/**
 * 团本治疗天梯（排名数据）
 *
 * 专精图标与职业信息统一见 specs.js，此处只保留层级与元数据。
 * 来源: https://www.wowhead.com/cn/guide/classes/tier-lists/healer-rankings-raids
 * 更新: 2026/11/10
 *
 * 由 tools/fetch_tier_lists.py 自动生成，请勿手改。
 */

const healerTierList = {
  "title": "Healer Raid Rankings - Tier List for Midnight Season 2",
  "source": "Wowhead",
  "lastUpdated": "2026/11/10",
  "fetchedAt": "2026/11/10",
  "sourceUrl": "https://www.wowhead.com/cn/guide/classes/tier-lists/healer-rankings-raids",
  "tiers": {
    "S": {
      "name": "S",
      "description": "",
      "specs": [
        "evoker|恩护"
      ]
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
        "druid|恢复",
        "priest|戒律",
        "priest|神圣",
        "shaman|恢复"
      ]
    },
    "B": {
      "name": "B",
      "description": "",
      "specs": [
        "paladin|神圣",
        "monk|织雾"
      ]
    },
    "C": {
      "name": "C",
      "description": "",
      "specs": []
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

export default healerTierList;
