export interface EntryInfo {
  id: number;
  player_first_name: string;
  player_last_name: string;
  player_region_name: string;
  player_region_iso_code_short: string;
  player_region_iso_code_long: string;
  summary_overall_points: number;
  summary_overall_rank: number;
  summary_event_points: number;
  summary_event_rank: number;
  current_event: number;
  name: string; 
  kit?: string;
}

export interface Player {
  id: number;
  web_name: string;
  team_code: number;
  element_type: number;
  now_cost: number;
  selected_by_percent: string;
  form: string;
  total_points: number;
}

export interface GameweekLive {
  id: number;
  points: number;
  rank: number;
  rank_sort: number;
  overall_rank: number;
  percentile_rank: number;
}

export interface NewsArticle {
  title: string;
  description: string;
  url: string;
  urlToImage: string;
  publishedAt: string;
  source: {
    name: string;
  };
  relevance_score?: number;
}

export interface Prediction {
  element: number;
  round: number;
  predicted_points: number;
  model_version: string;
}

export interface Recommendation {
  element_in: Player;
  element_out: Player;
  score: number;
  reasoning: string;
}

export interface MLReport {
  header: {
    manager: string;
    team: string;
    gameweek: number;
    generated: string;
  };
  current_squad: Array<{
    player: string;
    team: string;
    pos: number;
    price: number;
    xp: number;
  }>;
  fixture_insights: {
    best_fixture_runs: Array<{
      player: string;
      team: string;
      avg_fdr: number;
    }>;
    dgw_alerts: Array<{
      team: string;
      probability: number;
    }>;
    bgw_alerts: Array<{
      team: string;
    }>;
  };
  transfer_recommendations: {
    top_suggestion: {
      num_transfers: number;
      net_ev_gain: number;
      net_ev_gain_adjusted?: number;
      penalty_hits?: number;
      hit_reason?: string | null;
      players_out: Array<{
        id: number | null;
        name: string;
        team: string;
        element_type: number;
        form: number | null;
        ev: number;
        ownership: number | null;
        points_per_game: number | null;
        fdr: number | null;
      }>;
      players_in: Array<{
        id: number | null;
        name: string;
        team: string;
        element_type: number;
        form: number | null;
        ev: number;
        ownership: number | null;
        points_per_game: number | null;
        fdr: number | null;
      }>;
    } | null;
    best_no_hit?: {
      num_transfers: number;
      net_ev_gain: number;
      net_ev_gain_adjusted: number;
      penalty_hits: number;
      players_out: Array<any>;
      players_in: Array<any>;
    } | null;
    best_hit?: {
      num_transfers: number;
      net_ev_gain: number;
      net_ev_gain_adjusted: number;
      penalty_hits: number;
      hit_reason?: string | null;
      players_out: Array<any>;
      players_in: Array<any>;
    } | null;
    hit_vs_no_hit_comparison?: {
      better_option: "hit" | "no_hit";
      reason: string;
      hit_net_gain: number | null;
      no_hit_net_gain: number | null;
      difference: number | null;
    } | null;
  };
  updated_squad: {
    starting_xi: Array<{
      player: string;
      team: string;
      pos: number;
      price: number;
      xp: number;
      fixture: string;
    }>;
    bench: Array<{
      player: string;
      team: string;
      pos: number;
      price: number;
      xp: number;
      fixture: string;
    }>;
  };
  chip_recommendation: {
    best_chip: string;
    evaluations: {
      [key: string]: {
        recommend: boolean;
        ev_gain: number;
        reason: string;
      };
    };
  };
  captain_recommendations?: {
    captain: {
      id: number;
      name: string;
      team: string;
      ev: number;
      form: number | null;
      fdr: number;
      captain_score: number;
      reason: string;
    } | null;
    vice_captain: {
      id: number;
      name: string;
      team: string;
      ev: number;
      form: number | null;
      fdr: number;
      captain_score: number;
      reason: string;
    } | null;
    reason?: string;
  };
}
