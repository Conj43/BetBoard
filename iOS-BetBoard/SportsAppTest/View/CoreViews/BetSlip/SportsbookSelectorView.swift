//
//  SportsbookSelectorView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//


//
//  SportsbookSelectorView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct SportsbookSelectorView: View {
    let availableSportsbooks: [Sportsbook]
    @Binding var selectedSportsbook: Sportsbook
    
    var body: some View {
        Group {
            if availableSportsbooks.count > 1 {
                multipleSportsbooksView
            } else {
                singleSportsbookView
            }
        }
    }
    
    // MARK: - Multiple Sportsbooks
    private var multipleSportsbooksView: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Sportsbook")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(.secondary)
                
                Spacer()
            }
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(availableSportsbooks, id: \.self) { sportsbook in
                        SportsbookButton(
                            sportsbook: sportsbook,
                            isSelected: selectedSportsbook == sportsbook
                        ) {
                            selectedSportsbook = sportsbook
                        }
                    }
                }
                .padding(.horizontal, 1)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color(.systemBackground))
        .overlay(
            Rectangle()
                .fill(Color(.systemGray4))
                .frame(height: 1),
            alignment: .bottom
        )
    }
    
    // MARK: - Single Sportsbook
    private var singleSportsbookView: some View {
        HStack {
            RoundedRectangle(cornerRadius: 8)
                .fill(SportsbookHelper.color(for: selectedSportsbook))
                .frame(width: 40, height: 30)
                .overlay(
                    Text(SportsbookHelper.initials(for: selectedSportsbook))
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                )
            
            Text(selectedSportsbook.displayName)
                .font(.subheadline)
                .fontWeight(.medium)
            
            Spacer()
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color(.systemBackground))
        .overlay(
            Rectangle()
                .fill(Color(.systemGray4))
                .frame(height: 1),
            alignment: .bottom
        )
    }
}

// MARK: - Sportsbook Button
struct SportsbookButton: View {
    let sportsbook: Sportsbook
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(SportsbookHelper.color(for: sportsbook))
                    .frame(width: 22, height: 16)
                    .overlay(
                        Text(SportsbookHelper.initials(for: sportsbook))
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.white)
                    )
                
                Text(sportsbook.displayName)
                    .font(.system(size: 13, weight: .medium))
                    .lineLimit(1)
                    .fixedSize()
            }
            .foregroundColor(isSelected ? .white : .primary)
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(isSelected ? Color.blue : Color(.systemGray6))
            .cornerRadius(20)
        }
    }
}

// MARK: - Sportsbook Helper
struct SportsbookHelper {
    static func color(for sportsbook: Sportsbook) -> Color {
        switch sportsbook {
        case .draftkings:
            return Color(red: 0.0, green: 0.31, blue: 0.15)
        case .fanduel:
            return Color(red: 0.0, green: 0.36, blue: 0.82)
        case .betmgm:
            return Color(red: 0.83, green: 0.69, blue: 0.22)
        case .caesars:
            return Color(red: 0.8, green: 0.0, blue: 0.13)
        case .pointsbet:
            return Color(red: 0.0, green: 0.2, blue: 0.4)
        case .barstool:
            return Color(red: 0.95, green: 0.4, blue: 0.76)
        }
    }
    
    static func initials(for sportsbook: Sportsbook) -> String {
        switch sportsbook {
        case .draftkings: return "DK"
        case .fanduel: return "FD"
        case .betmgm: return "MGM"
        case .caesars: return "CZR"
        case .pointsbet: return "PB"
        case .barstool: return "BS"
        }
    }
}