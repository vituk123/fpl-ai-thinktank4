"""
Markdown report generator for FPL analysis.
"""
import pandas as pd
from typing import Dict, List
from datetime import datetime
import logging
from .utils import create_markdown_table

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generator for comprehensive FPL analysis reports."""
    
    def __init__(self, config: Dict):
        """
        Initialize report generator.
        """
        self.config = config
    
    def _generate_header(self, entry_info: Dict, gameweek: int) -> str:
        """Generate report header."""
        return f"""# FPL Analysis Report - GW{gameweek}

**Manager:** {entry_info.get('player_first_name')} {entry_info.get('player_last_name')}
**Team:** {entry_info.get('name')}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---"""

    def _generate_squad_analysis(self, current_squad: pd.DataFrame) -> str:
        """Generate squad analysis section."""
        if current_squad.empty:
            return "## Current Squad Analysis\n\nCould not retrieve current squad."

        squad_df = current_squad[['web_name', 'team_name', 'position', 'now_cost', 'EV']].copy()
        squad_df['now_cost'] = squad_df['now_cost'] / 10.0
        squad_df.rename(columns={'web_name': 'Player', 'team_name': 'Team', 'position': 'Pos', 'now_cost': 'Price', 'EV': 'xP'}, inplace=True)
        
        return "## Current Squad Analysis\n\n" + create_markdown_table(squad_df.sort_values(by='xP', ascending=False))

    def _apply_transfers_to_squad(self, current_squad: pd.DataFrame, recommendation: Dict, all_players: pd.DataFrame) -> pd.DataFrame:
        """Apply transfers to current squad and return updated squad."""
        updated_squad = current_squad.copy()
        
        # Remove players going out
        for player_out in recommendation.get('players_out', []):
            player_name = player_out['name']
            # Use ID if available for precise matching
            if 'id' in player_out:
                updated_squad = updated_squad[updated_squad['id'] != player_out['id']]
            else:
                updated_squad = updated_squad[updated_squad['web_name'] != player_name]
        
        # Add players coming in
        for player_in in recommendation.get('players_in', []):
            player_name = player_in['name']
            player_team = player_in.get('team', '')
            
            # Find player in all_players - prefer ID if available
            if 'id' in player_in:
                new_player = all_players[all_players['id'] == player_in['id']]
            else:
                # Match by name and team to handle duplicate names (e.g., Henderson)
                if player_team:
                    new_player = all_players[
                        (all_players['web_name'] == player_name) & 
                        (all_players['team_name'] == player_team)
                    ]
                else:
                    # Fallback: just by name, but take first match only
                    new_player = all_players[all_players['web_name'] == player_name]
                    if len(new_player) > 1:
                        # If multiple matches, prefer the one with higher EV
                        new_player = new_player.nlargest(1, 'EV')
            
            if not new_player.empty:
                # Only add if not already in squad (avoid duplicates)
                player_id = new_player.iloc[0]['id']
                if player_id not in updated_squad['id'].values:
                    updated_squad = pd.concat([updated_squad, new_player.iloc[[0]]], ignore_index=True)
        
        return updated_squad
    
    def _build_starting_xi(self, squad: pd.DataFrame) -> pd.DataFrame:
        """
        Build starting XI from squad (top 11 by EV, respecting formation).
        Uses adjusted FDR as a tie-breaker when EV values are similar.
        """
        if len(squad) < 11:
            return squad.nlargest(len(squad), 'EV')
        
        # Create a composite score: EV (primary) + inverse FDR (tie-breaker)
        # Lower FDR = easier fixture = higher score
        # Use fdr_adjusted if available, otherwise fallback to fdr
        if 'fdr_adjusted' in squad.columns:
            fdr_col = 'fdr_adjusted'
        elif 'fdr' in squad.columns:
            fdr_col = 'fdr'
        else:
            fdr_col = None
        
        if fdr_col:
            # Normalize FDR to 0-1 scale (inverse: lower FDR = higher score)
            # FDR range is 1-5, so inverse = (6 - FDR) / 5
            squad = squad.copy()
            squad['_fdr_score'] = (6 - pd.to_numeric(squad[fdr_col], errors='coerce').fillna(3.0)) / 5.0
            # Create composite score: EV + small FDR bonus (acts as tie-breaker)
            # FDR bonus is small (0.1 * normalized FDR) so it only affects when EV is similar
            squad['_composite_score'] = pd.to_numeric(squad.get('EV', 0), errors='coerce').fillna(0) + (0.1 * squad['_fdr_score'])
            squad_sorted = squad.sort_values('_composite_score', ascending=False)
        else:
            # Fallback to EV only if no FDR available
            squad_sorted = squad.sort_values('EV', ascending=False)
        
        # FPL formation constraints: min 1 GKP, 3 DEF, 3 MID, 1 FWD
        # Max: 1 GKP, 5 DEF, 5 MID, 3 FWD
        starting_xi = []
        gkp_count = 0
        def_count = 0
        mid_count = 0
        fwd_count = 0
        
        # First pass: ensure minimums
        for _, player in squad_sorted.iterrows():
            if len(starting_xi) >= 11:
                break
            
            pos = player['element_type']
            if pos == 1 and gkp_count < 1:  # GKP (max 1)
                starting_xi.append(player)
                gkp_count += 1
            elif pos == 2 and def_count < 3:  # DEF (min 3)
                starting_xi.append(player)
                def_count += 1
            elif pos == 3 and mid_count < 3:  # MID (min 3)
                starting_xi.append(player)
                mid_count += 1
            elif pos == 4 and fwd_count < 1:  # FWD (min 1)
                starting_xi.append(player)
                fwd_count += 1
        
        # Second pass: fill remaining slots (respecting position limits)
        for _, player in squad_sorted.iterrows():
            if len(starting_xi) >= 11:
                break
            if player['id'] in [p['id'] for p in starting_xi]:
                continue
            
            pos = player['element_type']
            # Check position limits before adding
            if pos == 1 and gkp_count >= 1:  # Already have 1 GK, skip
                continue
            elif pos == 2 and def_count >= 5:  # Max 5 DEF
                continue
            elif pos == 3 and mid_count >= 5:  # Max 5 MID
                continue
            elif pos == 4 and fwd_count >= 3:  # Max 3 FWD
                continue
            
            starting_xi.append(player)
            # Update counts
            if pos == 1:
                gkp_count += 1
            elif pos == 2:
                def_count += 1
            elif pos == 3:
                mid_count += 1
            elif pos == 4:
                fwd_count += 1
        
        return pd.DataFrame(starting_xi)
    
    def _get_fixture_info(self, player: pd.Series, fixtures: List[Dict], team_map: Dict) -> str:
        """Get opponent information for a player."""
        player_team_id = player['team']
        
        for fixture in fixtures:
            if fixture.get('team_a') == player_team_id:
                opponent_id = fixture.get('team_h')
                opponent_name = team_map.get(opponent_id, 'Unknown')
                return f"vs {opponent_name}"
            elif fixture.get('team_h') == player_team_id:
                opponent_id = fixture.get('team_a')
                opponent_name = team_map.get(opponent_id, 'Unknown')
                return f"vs {opponent_name}"
        
        return "No fixture"
    
    def _generate_updated_squad_section(self, current_squad: pd.DataFrame, recommendation: Dict, all_players: pd.DataFrame, fixtures: List[Dict], team_map: Dict) -> str:
        """Generate updated squad section after transfers."""
        from .utils import price_from_api
        
        if not recommendation:
            return ""
        
        # Apply transfers
        updated_squad = self._apply_transfers_to_squad(current_squad, recommendation, all_players)
        
        # Build starting XI
        starting_xi = self._build_starting_xi(updated_squad)
        starting_xi_ids = set(starting_xi['id'])
        
        # Bench (remaining players)
        bench = updated_squad[~updated_squad['id'].isin(starting_xi_ids)]
        
        content = "\n## Updated Squad After Transfers\n\n"
        
        # Starting XI
        if not starting_xi.empty:
            starting_xi_display = starting_xi.copy()
            starting_xi_display['price'] = starting_xi_display['now_cost'].apply(price_from_api)
            starting_xi_display['opponent'] = starting_xi_display.apply(
                lambda row: self._get_fixture_info(row, fixtures, team_map), axis=1
            )
            
            display_cols = ['web_name', 'team_name', 'position', 'price', 'EV', 'opponent']
            starting_xi_display = starting_xi_display[display_cols].copy()
            starting_xi_display.rename(columns={
                'web_name': 'Player',
                'team_name': 'Team',
                'position': 'Pos',
                'price': 'Price',
                'EV': 'xP',
                'opponent': 'Fixture'
            }, inplace=True)
            starting_xi_display = starting_xi_display.sort_values('xP', ascending=False)
            
            content += "### Starting XI\n\n"
            content += create_markdown_table(starting_xi_display)
            content += "\n"
        
        # Bench
        if not bench.empty:
            bench_display = bench.copy()
            bench_display['price'] = bench_display['now_cost'].apply(price_from_api)
            bench_display['opponent'] = bench_display.apply(
                lambda row: self._get_fixture_info(row, fixtures, team_map), axis=1
            )
            
            display_cols = ['web_name', 'team_name', 'position', 'price', 'EV', 'opponent']
            bench_display = bench_display[display_cols].copy()
            bench_display.rename(columns={
                'web_name': 'Player',
                'team_name': 'Team',
                'position': 'Pos',
                'price': 'Price',
                'EV': 'xP',
                'opponent': 'Fixture'
            }, inplace=True)
            bench_display = bench_display.sort_values('xP', ascending=False)
            
            content += "### Bench\n\n"
            content += create_markdown_table(bench_display)
            content += "\n"
        
        return content
    
    def _generate_transfer_recommendations(self, recommendations: List[Dict]) -> str:
        """Generate transfer recommendations section."""
        if not recommendations:
            return "## Transfer Recommendations\n\nNo beneficial transfers found."

        rec = recommendations[0]
        # Include team names to avoid ambiguity (e.g., multiple players named Henderson)
        out_players = ', '.join([f"{p['name']} ({p.get('team', 'Unknown')})" for p in rec['players_out']])
        in_players = ', '.join([f"{p['name']} ({p.get('team', 'Unknown')})" for p in rec['players_in']])
        
        return f"""## Transfer Recommendations

**Top Suggestion:** {rec['num_transfers']} transfer(s) with a net EV gain of **{rec['net_ev_gain']:.2f}**.

*   **Out:** {out_players}
*   **In:** {in_players}
"""

    def _generate_chip_evaluation(self, chip_evaluation: Dict) -> str:
        """Generate chip evaluation section."""
        best_chip_raw = chip_evaluation.get('best_chip') or 'NO CHIP'
        best_chip = str(best_chip_raw).replace('_', ' ').title()
        
        content = f"## Chip Recommendation\n\n**Suggestion:** Play **{best_chip}**.\n\n"
        
        for chip_name, result in chip_evaluation.get('evaluations', {}).items():
            content += f"- **{chip_name.replace('_', ' ').title()}:** {result['reason']}.\n"
        
        # If Triple Captain is recommended, show the captain suggestion
        if best_chip_raw == 'triple_captain':
            tc_result = chip_evaluation.get('evaluations', {}).get('triple_captain', {})
            if 'captain' in tc_result:
                content += f"\n### Triple Captain Suggestion\n\n"
                content += f"**Captain:** {tc_result['captain']} ({tc_result.get('captain_team', 'Unknown')})\n\n"
                content += f"**Source:** {tc_result.get('captain_source', 'current squad')}\n"
                content += f"**Expected Points:** {tc_result.get('captain_ev', 0):.2f}\n"
        
        # If Free Hit is recommended, show the optimal squad
        if best_chip_raw == 'free_hit':
            fh_result = chip_evaluation.get('evaluations', {}).get('free_hit', {})
            if 'optimal_squad' in fh_result and not fh_result['optimal_squad'].empty:
                content += self._generate_free_hit_squad(fh_result['optimal_squad'], fh_result.get('starting_xi', pd.DataFrame()))
        
        # If Wildcard is recommended, show the optimal squad
        if best_chip_raw == 'wildcard':
            wc_result = chip_evaluation.get('evaluations', {}).get('wildcard', {})
            if 'optimal_squad' in wc_result and not wc_result['optimal_squad'].empty:
                content += self._generate_wildcard_squad(wc_result['optimal_squad'], wc_result.get('starting_xi', pd.DataFrame()))
            
        return content
    
    def _generate_free_hit_squad(self, squad: pd.DataFrame, starting_xi: pd.DataFrame) -> str:
        """Generate Free Hit squad section."""
        from .utils import price_from_api
        
        if squad.empty:
            return "\n\n**Free Hit Squad:** Could not generate optimal squad.\n"
        
        content = "\n\n### Free Hit Optimal Squad\n\n"
        
        # Starting XI
        if not starting_xi.empty and 'in_starting_xi' in squad.columns:
            starting_xi_df = squad[squad['in_starting_xi'] == True].copy()
        else:
            # Fallback: top 11 by EV
            starting_xi_df = squad.nlargest(11, 'EV').copy()
        
        if not starting_xi_df.empty:
            starting_xi_df['price'] = starting_xi_df['now_cost'].apply(price_from_api)
            starting_xi_display = starting_xi_df[['web_name', 'team_name', 'position', 'price', 'EV']].copy()
            starting_xi_display.rename(columns={
                'web_name': 'Player', 
                'team_name': 'Team', 
                'position': 'Pos', 
                'price': 'Price', 
                'EV': 'xP'
            }, inplace=True)
            starting_xi_display = starting_xi_display.sort_values('xP', ascending=False)
            
            content += "#### Starting XI\n\n"
            content += create_markdown_table(starting_xi_display)
            content += "\n"
        
        # Bench
        if 'in_starting_xi' in squad.columns:
            bench_df = squad[squad['in_starting_xi'] == False].copy()
        else:
            bench_df = squad.nsmallest(4, 'EV').copy()
        
        if not bench_df.empty:
            bench_df['price'] = bench_df['now_cost'].apply(price_from_api)
            bench_display = bench_df[['web_name', 'team_name', 'position', 'price', 'EV']].copy()
            bench_display.rename(columns={
                'web_name': 'Player', 
                'team_name': 'Team', 
                'position': 'Pos', 
                'price': 'Price', 
                'EV': 'xP'
            }, inplace=True)
            bench_display = bench_display.sort_values('xP', ascending=False)
            
            content += "#### Bench\n\n"
            content += create_markdown_table(bench_display)
            content += "\n"
        
        # Squad summary
        total_ev = squad['EV'].sum()
        total_cost = squad['now_cost'].apply(price_from_api).sum()
        content += f"\n**Total Squad EV:** {total_ev:.2f}  \n"
        content += f"**Total Squad Cost:** £{total_cost:.1f}m\n"
        
        return content
    
    def _generate_wildcard_squad(self, squad: pd.DataFrame, starting_xi: pd.DataFrame) -> str:
        """Generate Wildcard squad section (same format as Free Hit)."""
        content = self._generate_free_hit_squad(squad, starting_xi)
        # Replace "Free Hit" with "Wildcard" in the title
        content = content.replace("### Free Hit Optimal Squad", "### Wildcard Optimal Squad")
        return content

    def _generate_fixture_insights(self, players_df: pd.DataFrame, gameweek: int) -> str:
        """Generate fixture analysis insights section."""
        if players_df.empty:
            return ""
        
        insights = ["## Fixture Analysis Insights\n"]
        
        # Check if advanced fixture features exist
        has_advanced = any(col in players_df.columns for col in ['fdr_3gw', 'fdr_5gw', 'fdr_8gw', 'dgw_probability', 'bgw_probability'])
        
        if not has_advanced:
            return ""
        
        # Rolling FDR summary
        if 'fdr_3gw' in players_df.columns:
            best_3gw = players_df.nsmallest(5, 'fdr_3gw')[['web_name', 'team_name', 'fdr_3gw']]
            insights.append("### Best Fixture Runs (Next 3 GWs)\n")
            insights.append("| Player | Team | Avg FDR |\n| --- | --- | --- |\n")
            for _, row in best_3gw.iterrows():
                insights.append(f"| {row['web_name']} | {row['team_name']} | {row['fdr_3gw']:.2f} |\n")
            insights.append("\n")
        
        # DGW/BGW alerts
        if 'dgw_probability' in players_df.columns:
            dgw_teams = players_df[players_df['dgw_probability'] > 0.5].groupby('team_name')['dgw_probability'].first()
            if not dgw_teams.empty:
                insights.append("### Double Gameweek Alerts\n")
                insights.append("Teams with potential DGW:\n")
                for team, prob in dgw_teams.items():
                    insights.append(f"- **{team}**: {prob:.0%} probability\n")
                insights.append("\n")
        
        if 'bgw_probability' in players_df.columns:
            bgw_teams = players_df[players_df['bgw_probability'] > 0.5]['team_name'].unique()
            if len(bgw_teams) > 0:
                insights.append("### Blank Gameweek Alerts\n")
                insights.append("Teams likely to blank:\n")
                for team in bgw_teams:
                    insights.append(f"- **{team}**\n")
                insights.append("\n")
        
        # Congestion alerts
        if 'rotation_risk' in players_df.columns:
            high_risk = players_df[players_df['rotation_risk'] == 'high']
            if not high_risk.empty:
                insights.append("### Rotation Risk Alerts\n")
                insights.append("Players with high rotation risk (low rest days):\n")
                for _, row in high_risk.head(10).iterrows():
                    rest_days = row.get('rest_days', 'N/A')
                    insights.append(f"- **{row['web_name']}** ({row['team_name']}): {rest_days} rest days\n")
                insights.append("\n")
        
        return "".join(insights)
    
    def generate_report(self, entry_info: Dict, gameweek: int, current_squad: pd.DataFrame, recommendations: List[Dict], chip_evaluation: Dict, players_df: pd.DataFrame, output_path: str, fixtures: List[Dict] = None, team_map: Dict = None):
        """
        Generate comprehensive Markdown report.
        """
        report_parts = [
            self._generate_header(entry_info, gameweek),
            self._generate_squad_analysis(current_squad),
            self._generate_fixture_insights(players_df, gameweek),
            self._generate_transfer_recommendations(recommendations),
        ]
        
        # Add updated squad section if transfers are recommended
        if recommendations and len(recommendations) > 0 and fixtures and team_map:
            report_parts.append(
                self._generate_updated_squad_section(
                    current_squad,
                    recommendations[0],
                    players_df,
                    fixtures,
                    team_map
                )
            )
        
        report_parts.append(self._generate_chip_evaluation(chip_evaluation))
        
        full_report = "\n".join(report_parts)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_report)
        
        logger.info(f"Report successfully generated at {output_path}")
    
    def generate_report_data(self, entry_info: Dict, gameweek: int, current_squad: pd.DataFrame, recommendations: List[Dict], chip_evaluation: Dict, players_df: pd.DataFrame, fixtures: List[Dict] = None, team_map: Dict = None, bootstrap: Dict = None) -> Dict:
        """
        Generate report data as JSON structure (same as generate_report but returns dict instead of markdown).
        """
        from datetime import datetime
        import numpy as np
        from .utils import price_from_api
        
        def to_python_type(value):
            """Convert numpy types to native Python types for JSON serialization"""
            if isinstance(value, (np.integer, np.int8, np.int16, np.int32, np.int64)):
                return int(value)
            elif isinstance(value, (np.floating, np.float16, np.float32, np.float64)):
                return float(value)
            elif isinstance(value, np.bool_):
                return bool(value)
            elif isinstance(value, np.ndarray):
                return value.tolist()
            elif pd.isna(value):
                return None
            return value
        
        # Header
        header = {
            "manager": f"{entry_info.get('player_first_name', '')} {entry_info.get('player_last_name', '')}".strip(),
            "team": entry_info.get('name', 'Unknown'),
            "gameweek": gameweek,
            "generated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Current Squad Analysis
        current_squad_list = []
        if not current_squad.empty:
            squad_df = current_squad[['web_name', 'team_name', 'element_type', 'now_cost', 'EV']].copy()
            squad_df = squad_df.sort_values(by='EV', ascending=False)
            for _, row in squad_df.iterrows():
                current_squad_list.append({
                    "player": str(row['web_name']),
                    "team": str(row['team_name']),
                    "pos": to_python_type(row['element_type']),
                    "price": to_python_type(row['now_cost'] / 10.0),
                    "xp": to_python_type(row['EV'])
                })
        
        # Fixture Insights
        fixture_insights = {
            "best_fixture_runs": [],
            "dgw_alerts": [],
            "bgw_alerts": []
        }
        
        if not players_df.empty and 'fdr_3gw' in players_df.columns:
            best_3gw = players_df.nsmallest(5, 'fdr_3gw')[['web_name', 'team_name', 'fdr_3gw']]
            for _, row in best_3gw.iterrows():
                fixture_insights["best_fixture_runs"].append({
                    "player": str(row['web_name']),
                    "team": str(row['team_name']),
                    "avg_fdr": to_python_type(row['fdr_3gw'])
                })
        
        if 'dgw_probability' in players_df.columns:
            dgw_teams = players_df[players_df['dgw_probability'] > 0.5].groupby('team_name')['dgw_probability'].first()
            for team, prob in dgw_teams.items():
                fixture_insights["dgw_alerts"].append({
                    "team": str(to_python_type(team)),
                    "probability": to_python_type(prob)
                })
        
        if 'bgw_probability' in players_df.columns:
            bgw_teams = players_df[players_df['bgw_probability'] > 0.5]['team_name'].unique()
            fixture_insights["bgw_alerts"] = [{"team": str(to_python_type(team))} for team in bgw_teams]
        
        # Transfer Recommendations
        transfer_recommendations = {
            "top_suggestion": None,
            "best_no_hit": None,
            "best_hit": None,
            "hit_vs_no_hit_comparison": None
        }
        
        # Initialize top_rec outside the if block so it's accessible for updated squad
        top_rec = None
        
        if recommendations and len(recommendations) > 0:
            # Find best no-hit and best hit recommendations
            best_no_hit = None
            best_hit = None
            
            for rec in recommendations:
                penalty_hits = rec.get('penalty_hits', 0)
                net_ev_gain_adjusted = rec.get('net_ev_gain_adjusted', rec.get('net_ev_gain', 0))
                
                if penalty_hits == 0:
                    # No-hit recommendation
                    if best_no_hit is None or net_ev_gain_adjusted > best_no_hit.get('net_ev_gain_adjusted', best_no_hit.get('net_ev_gain', 0)):
                        best_no_hit = rec
                else:
                    # Hit recommendation
                    if best_hit is None or net_ev_gain_adjusted > best_hit.get('net_ev_gain_adjusted', best_hit.get('net_ev_gain', 0)):
                        best_hit = rec
            
            # Compare hit vs no-hit
            comparison = None
            if best_no_hit and best_hit:
                no_hit_gain = best_no_hit.get('net_ev_gain_adjusted', best_no_hit.get('net_ev_gain', 0))
                hit_gain = best_hit.get('net_ev_gain_adjusted', best_hit.get('net_ev_gain', 0))
                hit_penalty = best_hit.get('penalty_hits', 0) * 4
                
                difference = hit_gain - no_hit_gain
                if difference >= 5.0:
                    comparison = {
                        "better_option": "hit",
                        "reason": f"Taking a -{hit_penalty} point hit provides a net gain of {hit_gain:.2f} points, which is {difference:.2f} points better than the best no-hit option ({no_hit_gain:.2f} points). This exceeds the 5-point threshold, so the hit transfer is recommended.",
                        "hit_net_gain": hit_gain,
                        "no_hit_net_gain": no_hit_gain,
                        "difference": difference
                    }
                else:
                    comparison = {
                        "better_option": "no_hit",
                        "reason": f"The best no-hit option provides {no_hit_gain:.2f} points, which is {abs(difference):.2f} points better than taking a -{hit_penalty} point hit ({hit_gain:.2f} points). Since the hit transfer is not at least 5 points better, the no-hit option is recommended.",
                        "hit_net_gain": hit_gain,
                        "no_hit_net_gain": no_hit_gain,
                        "difference": difference
                    }
            elif best_hit and not best_no_hit:
                comparison = {
                    "better_option": "hit",
                    "reason": "Only hit transfer options are available. No free transfer options found.",
                    "hit_net_gain": best_hit.get('net_ev_gain_adjusted', best_hit.get('net_ev_gain', 0)),
                    "no_hit_net_gain": None,
                    "difference": None
                }
            elif best_no_hit and not best_hit:
                comparison = {
                    "better_option": "no_hit",
                    "reason": "No hit transfer options are available. All recommendations use free transfers only.",
                    "hit_net_gain": None,
                    "no_hit_net_gain": best_no_hit.get('net_ev_gain_adjusted', best_no_hit.get('net_ev_gain', 0)),
                    "difference": None
                }
            
            # Helper function to get player stats from players_df
            def get_player_stats(player_dict):
                """Extract player stats from players_df using player ID."""
                player_id = player_dict.get('id')
                if not player_id or players_df.empty:
                    # Fallback to basic info if ID not available
                    return {
                        "id": None,
                        "name": str(to_python_type(player_dict.get('name', ''))),
                        "team": str(to_python_type(player_dict.get('team', 'Unknown'))),
                        "element_type": to_python_type(player_dict.get('element_type', 0)),
                        "form": None,
                        "ev": to_python_type(player_dict.get('EV', 0)),
                        "ownership": None,
                        "points_per_game": None,
                        "fdr": to_python_type(player_dict.get('fdr', 3.0))
                    }
                
                # Look up player in players_df
                player_row = players_df[players_df['id'] == player_id]
                if player_row.empty:
                    # Fallback if player not found
                    return {
                        "id": to_python_type(player_id),
                        "name": str(to_python_type(player_dict.get('name', ''))),
                        "team": str(to_python_type(player_dict.get('team', 'Unknown'))),
                        "element_type": to_python_type(player_dict.get('element_type', 0)),
                        "form": None,
                        "ev": to_python_type(player_dict.get('EV', 0)),
                        "ownership": None,
                        "points_per_game": None,
                        "fdr": to_python_type(player_dict.get('fdr', 3.0))
                    }
                
                row = player_row.iloc[0]
                
                # Get form (from FPL API)
                form = row.get('form')
                if pd.isna(form) or form == '':
                    form = None
                else:
                    try:
                        form = float(to_python_type(form))
                    except:
                        form = None
                
                # Get ownership (selected_by_percent)
                ownership = row.get('selected_by_percent')
                if pd.isna(ownership) or ownership == '':
                    ownership = None
                else:
                    try:
                        ownership = float(to_python_type(ownership))
                    except:
                        ownership = None
                
                # Calculate points per game
                points_per_game = None
                total_points = row.get('total_points', 0)
                minutes = row.get('minutes', 0)
                if not pd.isna(total_points) and not pd.isna(minutes) and minutes > 0:
                    try:
                        points_per_game = float(to_python_type(total_points)) / float(to_python_type(minutes)) * 90
                    except:
                        points_per_game = None
                elif 'points_per_game' in row and not pd.isna(row['points_per_game']):
                    try:
                        points_per_game = float(to_python_type(row['points_per_game']))
                    except:
                        points_per_game = None
                
                # Get fixture difficulty (prefer fdr, fdr_3gw, fallback to fdr_next or fixture_difficulty)
                fdr = None
                for fdr_col in ['fdr', 'fdr_3gw', 'fdr_next', 'fixture_difficulty', 'fdr_custom']:
                    if fdr_col in row and not pd.isna(row[fdr_col]):
                        try:
                            fdr = float(to_python_type(row[fdr_col]))
                            break
                        except:
                            continue
                # Also check player_dict for fdr (from optimizer)
                if fdr is None and 'fdr' in player_dict:
                    fdr = to_python_type(player_dict.get('fdr', 3.0))
                if fdr is None:
                    fdr = 3.0  # Default FDR
                
                # Get EV (from recommendation or players_df)
                ev = to_python_type(player_dict.get('EV', row.get('EV', 0)))
                if pd.isna(ev):
                    ev = 0
                
                # Get element_type (position)
                element_type = to_python_type(row.get('element_type', player_dict.get('element_type', 0)))
                
                # Get now_cost (price in API units, e.g., 76 = £7.6m)
                # Priority: 1) player_dict (from optimizer), 2) row (from players_df)
                now_cost = None
                if 'now_cost' in player_dict and player_dict['now_cost'] is not None:
                    try:
                        now_cost = int(to_python_type(player_dict['now_cost']))
                    except:
                        pass
                
                if now_cost is None and 'now_cost' in row and not pd.isna(row['now_cost']):
                    try:
                        now_cost = int(to_python_type(row['now_cost']))
                    except:
                        pass
                
                if now_cost is None:
                    now_cost = 0  # Default to 0 if not found
                
                return {
                    "id": to_python_type(player_id),
                    "name": str(to_python_type(row.get('web_name', player_dict.get('name', '')))),
                    "team": str(to_python_type(row.get('team_name', player_dict.get('team', 'Unknown')))),
                    "element_type": element_type,
                    "form": form,
                    "ev": ev,
                    "ownership": ownership,
                    "points_per_game": points_per_game,
                    "fdr": fdr,
                    "now_cost": now_cost
                }
            
            transfer_recommendations["hit_vs_no_hit_comparison"] = comparison
            
            # CRITICAL: Apply 5-point threshold rule for selecting top suggestion
            # Only choose hit transfer if it's at least 5 points better than best no-hit
            HIT_THRESHOLD = 5.0
            top_rec = None
            
            if best_no_hit and best_hit:
                no_hit_gain = best_no_hit.get('net_ev_gain_adjusted', best_no_hit.get('net_ev_gain', 0))
                hit_gain = best_hit.get('net_ev_gain_adjusted', best_hit.get('net_ev_gain', 0))
                difference = hit_gain - no_hit_gain
                
                if difference >= HIT_THRESHOLD:
                    # Hit transfer is at least 5 points better - choose it
                    top_rec = best_hit
                    logger.info(f"ReportGenerator: Hit transfer selected (difference: {difference:.2f} >= {HIT_THRESHOLD})")
                else:
                    # Hit transfer is not 5 points better - choose no-hit
                    top_rec = best_no_hit
                    logger.info(f"ReportGenerator: No-hit transfer selected (difference: {difference:.2f} < {HIT_THRESHOLD})")
            elif best_no_hit:
                # Only no-hit available
                top_rec = best_no_hit
                logger.info("ReportGenerator: No-hit transfer selected (only option available)")
            elif best_hit:
                # Only hit available (forced transfers)
                top_rec = best_hit
                logger.info("ReportGenerator: Hit transfer selected (only option available)")
            else:
                # Fallback to original top recommendation
                top_rec = recommendations[0] if recommendations else None
                logger.warning("ReportGenerator: Using fallback recommendation")
            
            # Helper to build recommendation dict
            BLOCKED_PLAYER_IDS = {5, 241}  # Gabriel, Caicedo
            def build_rec_dict(rec_data):
                filtered_out = [p for p in rec_data.get('players_out', []) if p.get('id') not in BLOCKED_PLAYER_IDS]
                filtered_in = [p for p in rec_data.get('players_in', []) if p.get('id') not in BLOCKED_PLAYER_IDS]
                return {
                    "num_transfers": to_python_type(len(filtered_out)),
                    "net_ev_gain": to_python_type(rec_data.get('net_ev_gain', 0)),
                    "net_ev_gain_adjusted": to_python_type(rec_data.get('net_ev_gain_adjusted', rec_data.get('net_ev_gain', 0))),
                    "players_out": [get_player_stats(p) for p in filtered_out],
                    "players_in": [get_player_stats(p) for p in filtered_in],
                    "penalty_hits": to_python_type(rec_data.get('penalty_hits', 0)),
                    "hit_reason": rec_data.get('hit_reason')
                }
            
            # Process best no-hit recommendation
            if best_no_hit:
                transfer_recommendations["best_no_hit"] = build_rec_dict(best_no_hit)
            
            # Process best hit recommendation
            if best_hit:
                transfer_recommendations["best_hit"] = build_rec_dict(best_hit)
            
            # Top suggestion based on 5-point threshold rule
            if top_rec:
                transfer_recommendations["top_suggestion"] = build_rec_dict(top_rec)
        
        # Updated Squad After Transfers
        updated_squad = {
            "starting_xi": [],
            "bench": []
        }
        
        # Use top_rec (top_suggestion) for updated squad, not recommendations[0]
        # top_rec is the recommendation that was selected based on the 5-point threshold rule
        # Fallback to recommendations[0] if top_rec is None (shouldn't happen, but safety check)
        rec_for_squad = top_rec if top_rec else (recommendations[0] if recommendations and len(recommendations) > 0 else None)
        
        if rec_for_squad and fixtures and team_map:
            updated_squad_df = self._apply_transfers_to_squad(current_squad, rec_for_squad, players_df)
            starting_xi_df = self._build_starting_xi(updated_squad_df)
            starting_xi_ids = set(starting_xi_df['id'])
            bench_df = updated_squad_df[~updated_squad_df['id'].isin(starting_xi_ids)]
            
            # For updated squad, we want to show fixtures for the NEXT upcoming gameweek (deadline hasn't passed)
            # Find the next gameweek using bootstrap events (is_next flag) or by checking deadlines
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            next_gameweek = None
            
            # First, try to find gameweek with is_next=True flag (most reliable)
            if bootstrap and 'events' in bootstrap:
                events = bootstrap.get('events', [])
                next_event = next((e for e in events if e.get('is_next', False)), None)
                if next_event:
                    next_gameweek = next_event.get('id')
                    logger.debug(f"Found next gameweek using is_next flag: {next_gameweek}")
            
            # If is_next not found, find the first gameweek where deadline hasn't passed
            if not next_gameweek and bootstrap and 'events' in bootstrap:
                events = bootstrap.get('events', [])
                for event in sorted(events, key=lambda x: x.get('id', 0)):
                    deadline_str = event.get('deadline_time')
                    if deadline_str:
                        try:
                            deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                            # If deadline is in the future, this is the next upcoming gameweek
                            if deadline > now:
                                next_gameweek = event.get('id')
                                logger.debug(f"Found next gameweek by deadline check: {next_gameweek}")
                                break
                        except Exception:
                            pass
            
            # Fallback: use gameweek + 1 if we couldn't find next gameweek
            if not next_gameweek:
                next_gameweek = gameweek + 1
                logger.debug(f"Using fallback next gameweek: {next_gameweek}")
            
            next_gw_fixtures = [f for f in fixtures if f.get('event') == next_gameweek] if next_gameweek else []
            
            # Starting XI
            if not starting_xi_df.empty:
                starting_xi_df['price'] = starting_xi_df['now_cost'].apply(price_from_api)
                # Use next gameweek fixtures for the updated squad
                starting_xi_df['opponent'] = starting_xi_df.apply(
                    lambda row: self._get_fixture_info(row, next_gw_fixtures, team_map), axis=1
                )
                starting_xi_df = starting_xi_df.sort_values('EV', ascending=False)
                
                for _, row in starting_xi_df.iterrows():
                    updated_squad["starting_xi"].append({
                        "player": str(row['web_name']),
                        "team": str(row['team_name']),
                        "pos": to_python_type(row['element_type']),
                        "price": to_python_type(row['price']),
                        "xp": to_python_type(row['EV']),
                        "fixture": str(row.get('opponent', 'No fixture'))
                    })
            
            # Bench
            if not bench_df.empty:
                bench_df['price'] = bench_df['now_cost'].apply(price_from_api)
                # Use next gameweek fixtures for the updated squad
                bench_df['opponent'] = bench_df.apply(
                    lambda row: self._get_fixture_info(row, next_gw_fixtures, team_map), axis=1
                )
                bench_df = bench_df.sort_values('EV', ascending=False)
                
                for _, row in bench_df.iterrows():
                    updated_squad["bench"].append({
                        "player": str(row['web_name']),
                        "team": str(row['team_name']),
                        "pos": to_python_type(row['element_type']),
                        "price": to_python_type(row['price']),
                        "xp": to_python_type(row['EV']),
                        "fixture": str(row.get('opponent', 'No fixture'))
                    })
            
            # Captain and Vice-Captain recommendations for updated squad
            captain_recommendation = None
            vice_captain_recommendation = None
            
            if not starting_xi_df.empty:
                # Ensure fdr and form columns exist (add defaults if missing)
                if 'fdr' not in starting_xi_df.columns:
                    starting_xi_df['fdr'] = 3.0
                if 'form' not in starting_xi_df.columns:
                    starting_xi_df['form'] = 0.0
                
                # Convert form and fdr to numeric (handle strings)
                starting_xi_df['form'] = pd.to_numeric(starting_xi_df['form'], errors='coerce').fillna(0.0)
                starting_xi_df['fdr'] = pd.to_numeric(starting_xi_df['fdr'], errors='coerce').fillna(3.0)
                starting_xi_df['EV'] = pd.to_numeric(starting_xi_df['EV'], errors='coerce').fillna(0.0)
                
                # Calculate captain score: EV + form bonus + FDR bonus
                # Elite players (high form) and forwards get priority
                starting_xi_df['captain_score'] = starting_xi_df.apply(lambda row: (
                    float(row.get('EV', 0)) +
                    (float(row.get('form', 0)) * 0.3) +  # Form bonus
                    ((5.0 - float(row.get('fdr', 3.0))) * 0.5) +  # Lower FDR = easier fixture = bonus
                    (2.0 if to_python_type(row.get('element_type', 0)) == 4 else 0)  # Forwards get +2 bonus
                ), axis=1)
                
                # Sort by captain score
                starting_xi_sorted = starting_xi_df.sort_values('captain_score', ascending=False)
                
                # Best captain (highest score)
                if len(starting_xi_sorted) > 0:
                    best_captain_row = starting_xi_sorted.iloc[0]
                    captain_recommendation = {
                        "player": str(best_captain_row['web_name']),
                        "team": str(best_captain_row['team_name']),
                        "pos": to_python_type(best_captain_row['element_type']),
                        "xp": to_python_type(best_captain_row['EV']),
                        "form": to_python_type(best_captain_row.get('form', 0)),
                        "fdr": to_python_type(best_captain_row.get('fdr', 3.0)),
                        "fixture": str(best_captain_row.get('opponent', 'No fixture')),
                        "reason": f"Highest captain score ({best_captain_row['captain_score']:.2f}) based on EV, form, and fixture difficulty"
                    }
                
                # Best vice-captain (second highest score, or best if captain is unavailable)
                if len(starting_xi_sorted) > 1:
                    best_vice_row = starting_xi_sorted.iloc[1]
                    vice_captain_recommendation = {
                        "player": str(best_vice_row['web_name']),
                        "team": str(best_vice_row['team_name']),
                        "pos": to_python_type(best_vice_row['element_type']),
                        "xp": to_python_type(best_vice_row['EV']),
                        "form": to_python_type(best_vice_row.get('form', 0)),
                        "fdr": to_python_type(best_vice_row.get('fdr', 3.0)),
                        "fixture": str(best_vice_row.get('opponent', 'No fixture')),
                        "reason": f"Second highest captain score ({best_vice_row['captain_score']:.2f}) - good backup option"
                    }
                elif len(starting_xi_sorted) > 0:
                    # Only one player, use same as captain
                    best_vice_row = starting_xi_sorted.iloc[0]
                    vice_captain_recommendation = {
                        "player": str(best_vice_row['web_name']),
                        "team": str(best_vice_row['team_name']),
                        "pos": to_python_type(best_vice_row['element_type']),
                        "xp": to_python_type(best_vice_row['EV']),
                        "form": to_python_type(best_vice_row.get('form', 0)),
                        "fdr": to_python_type(best_vice_row.get('fdr', 3.0)),
                        "fixture": str(best_vice_row.get('opponent', 'No fixture')),
                        "reason": "Only one player in starting XI - same as captain"
                    }
            
            # Add captain/vice recommendations to updated_squad
            updated_squad["captain"] = captain_recommendation
            updated_squad["vice_captain"] = vice_captain_recommendation
        
        # Chip Recommendation
        best_chip_raw = chip_evaluation.get('best_chip') or 'NO CHIP'
        best_chip = str(to_python_type(best_chip_raw)).replace('_', ' ').title()
        
        chip_evaluations = {}
        for chip_name, result in chip_evaluation.get('evaluations', {}).items():
            chip_evaluations[str(to_python_type(chip_name))] = {
                "recommend": to_python_type(result.get('recommend', False)),
                "ev_gain": to_python_type(result.get('ev_gain', 0)),
                "reason": str(to_python_type(result.get('reason', '')))
            }
        
        chip_recommendation = {
            "best_chip": best_chip,
            "evaluations": chip_evaluations
        }
        
        # Final conversion to ensure all values are JSON-serializable
        def convert_dict_values(obj):
            """Recursively convert numpy types in dictionaries and lists"""
            if isinstance(obj, dict):
                return {str(k): convert_dict_values(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_dict_values(item) for item in obj]
            else:
                return to_python_type(obj)
        
        result = {
            "header": header,
            "current_squad": current_squad_list,
            "fixture_insights": fixture_insights,
            "transfer_recommendations": transfer_recommendations,
            "updated_squad": updated_squad,
            "chip_recommendation": chip_recommendation
        }
        
        # Final pass to convert any remaining numpy types
        return convert_dict_values(result)

