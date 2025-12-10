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
        """Build starting XI from squad (top 11 by EV, respecting formation)."""
        if len(squad) < 11:
            return squad.nlargest(len(squad), 'EV')
        
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
        from utils import price_from_api
        
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
        from utils import price_from_api
        
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

