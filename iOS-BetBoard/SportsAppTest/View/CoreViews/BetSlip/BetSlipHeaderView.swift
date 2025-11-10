//
//  BetSlipHeaderView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//


import SwiftUI

struct BetSlipHeaderView: View {
    let betSlip: BetSlip
    
    var body: some View {
        VStack(spacing: 4) {
            // Teams and logos
            HStack {
                TeamLogoView(team: betSlip.awayTeam, size: 40)
                
                Spacer()
                
                VStack(spacing: 4) {
                    Text("VS")
                        .fontWeight(.bold)
                        .foregroundColor(.secondary)
                    
                    Text(betSlip.formattedGameTime)
                        .font(.footnote)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                TeamLogoView(team: betSlip.homeTeam, size: 40)
            }
            
            // Team names
            HStack {
                Text(betSlip.awayTeam.shortName)
                    .font(.headline)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)
                
                Text(betSlip.homeTeam.shortName)
                    .font(.headline)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 16)
        .padding(.bottom, 12)
    }
}

// MARK: - Team Display View
struct TeamDisplayView: View {
    let team: Team
    let logoSize: CGFloat
    
    var body: some View {
        VStack(spacing: 8) {
            // Team logo
            TeamLogoView(team: team, size: logoSize)
            
            // Team name
            Text(team.displayName)
                .font(.headline)
                .fontWeight(.bold)
            
            // Ranking
            if let ranking = team.ranking {
                Text("#\(ranking)")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.blue)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(4)
            }
            
            // Record
            Text("(\(team.record.wins)-\(team.record.losses))")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}
