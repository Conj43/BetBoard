//
//  TeamLogoView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/30/25.
//


//
//  TeamLogoView.swift
//  SportsAppTest
//
//  Reusable component for displaying team logos
//

import SwiftUI

struct TeamLogoView: View {
    let team: Team
    let size: CGFloat
    
    init(team: Team, size: CGFloat = 40) {
        self.team = team
        self.size = size
    }
    
    var body: some View {
        Group {
            if let uiImage = TeamLogoHelper.loadLogo(for: team.shortName) {
                Image(uiImage: uiImage)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: size, height: size)
            } else {
                // Fallback placeholder with team initials
                Circle()
                    .fill(teamColor)
                    .frame(width: size, height: size)
                    .overlay(
                        Text(teamInitials)
                            .font(.system(size: size * 0.4, weight: .bold))
                            .foregroundColor(.white)
                    )
            }
        }
    }
    
    private var teamInitials: String {
        let words = team.shortName.components(separatedBy: " ")
        if words.count >= 2 {
            return String(words[0].prefix(1)) + String(words[1].prefix(1))
        }
        return String(team.shortName.prefix(min(2, team.shortName.count)))
    }
    
    private var teamColor: Color {
        if let colorHex = team.colorHex {
            return Color(hex: colorHex) ?? .gray
        }
        return .gray
    }
}

// Extension to create Color from hex string
extension Color {
    init?(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        
        guard Scanner(string: hex).scanHexInt64(&int) else {
            return nil
        }
        
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            return nil
        }
        
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

#Preview {
    VStack(spacing: 20) {
        TeamLogoView(
            team: Team(
                id: "duke",
                name: "Duke Blue Devils",
                shortName: "DUKE",
                logoURL: "",
                record: TeamRecord(wins: 23, losses: 8),
                conference: "ACC",
                ranking: 9,
                colorHex: "#001A57"
            ),
            size: 60
        )
        
        TeamLogoView(
            team: Team(
                id: "unc",
                name: "North Carolina Tar Heels",
                shortName: "UNC",
                logoURL: "",
                record: TeamRecord(wins: 21, losses: 10),
                conference: "ACC",
                ranking: 15,
                colorHex: "#4B9CD3"
            ),
            size: 60
        )
    }
    .padding()
}