//
//  TeamSearchResultRowView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 11/25/25.
//

import SwiftUI

struct TeamSearchResultRowView: View {
    let team: Team
    
    var body: some View {
        HStack(spacing: 12) {
            // Team Logo
            TeamLogoView(team: team, size: 50)
            
            // Team Info
            VStack(alignment: .leading, spacing: 4) {
                Text(team.name)
                    .font(.headline)
                    .fontWeight(.semibold)
                
                HStack(spacing: 8) {
                    // Record
                    Text("\(team.record.wins)-\(team.record.losses)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    // Conference
                    Text(team.conference)
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundColor(.white)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(Color.blue)
                        .cornerRadius(4)
                    
                    // Ranking (if available)
                    if let ranking = team.ranking {
                        Text("#\(ranking)")
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 3)
                            .background(Color.orange)
                            .cornerRadius(4)
                    }
                }
            }
            
            Spacer()
            
            // Chevron
            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
}
