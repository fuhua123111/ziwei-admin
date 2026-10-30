// 与后端领域模型对应的类型定义

export interface Star {
  name: string;
  type: string;
  brightness?: string;
  mutagen?: string;
}

export interface Palace {
  index: number;
  name: string;
  heavenly_stem: string;
  earthly_branch: string;
  is_body: number;
  major_stars: string; // 数据库中为逗号拼接
  minor_stars: string;
}

export interface PalaceRaw {
  index: number;
  name: string;
  heavenly_stem: string;
  earthly_branch: string;
  is_body_palace: boolean;
  is_original_palace: boolean;
  major_stars: Star[];
  minor_stars: Star[];
  adjective_stars: Star[];
  changsheng12: string;
  boshi12: string;
  jiangqian12: string;
  suiqian12: string;
  decadal_range: number[];
  ages: number[];
}

export interface Mutagen {
  label: string;
  stems: string;
  stars: string[];
}

export interface ChartRaw {
  solar_date: string;
  lunar_date: string;
  chinese_date: string;
  time_name: string;
  time_range: string;
  gender: string;
  zodiac: string;
  sign: string;
  soul: string;
  body: string;
  five_elements_class: string;
  soul_branch: string;
  body_branch: string;
  palaces: PalaceRaw[];
  mutagens: Mutagen[];
  copyright?: string;
}

export interface Chart {
  id: number;
  name: string;
  gender: string;
  solar_date: string;
  time_index: number;
  lunar_date: string;
  chinese_date: string;
  time_name: string;
  zodiac: string;
  sign: string;
  soul: string;
  body: string;
  five_elements: string;
  soul_branch: string;
  body_branch: string;
  note: string;
  tags: string;
  star_rating: number;
  created_at: string;
  updated_at: string;
  all_major?: string;
  palaces?: Palace[];
  raw?: ChartRaw;
}

export interface ListResponse {
  ok: boolean;
  total: number;
  page: number;
  size: number;
  pages: number;
  items: Chart[];
}

export interface Stats {
  total: number;
  male: number;
  female: number;
  top_stars: { stars: string; count: number }[];
  five_elements: { name: string; count: number }[];
}

export const TIME_OPTIONS = [
  "早子时（00:00~01:00）",
  "丑时（01:00~03:00）",
  "寅时（03:00~05:00）",
  "卯时（05:00~07:00）",
  "辰时（07:00~09:00）",
  "巳时（09:00~11:00）",
  "午时（11:00~13:00）",
  "未时（13:00~15:00）",
  "申时（15:00~17:00）",
  "酉时（17:00~19:00）",
  "戌时（19:00~21:00）",
  "亥时（21:00~23:00）",
  "晚子时（23:00~00:00）",
];

export const MAJOR_STAR_LIST = [
  "紫微", "天机", "太阳", "武曲", "天同", "廉贞",
  "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军",
];
