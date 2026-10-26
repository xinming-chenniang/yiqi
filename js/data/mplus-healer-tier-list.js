/**
 * 大秘境治疗天梯（排名数据）
 *
 * 专精图标与职业信息统一见 specs.js，此处只保留层级与元数据。
 * 来源: https://www.wowhead.com/cn/guide/classes/tier-lists/healer-rankings-mythic-plus
 * 更新: 2026/10/13
 *
 * 由 tools/fetch_tier_lists.py 自动生成，请勿手改。
 */

const mplusHealerTierList = {
  "title": "Mythic+ Healer Rankings - Tier List for Midnight Season 2",
  "source": "AutomaticJak",
  "lastUpdated": "2026/10/13",
  "fetchedAt": "2026/10/26",
  "sourceUrl": "https://www.wowhead.com/cn/guide/classes/tier-lists/healer-rankings-mythic-plus",
  "tiers": {
    "S": {
      "name": "S",
      "description": "",
      "specs": [
        "paladin|神圣"
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
        "shaman|恢复"
      ]
    },
    "B": {
      "name": "B",
      "description": "",
      "specs": [
        "priest|神圣",
        "evoker|恩护",
        "monk|织雾"
      ]
    },
    "C": {
      "name": "C",
      "description": "",
      "specs": [
        "priest|戒律",
        "druid|恢复"
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

export default mplusHealerTierList;
