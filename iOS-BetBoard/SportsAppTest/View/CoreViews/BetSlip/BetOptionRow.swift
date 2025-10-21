//
//  BetOptionRow.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//


import SwiftUI

struct BetOptionRow: View {
    let selection: String
    let odds: Double
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(selection)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.primary)
                    
                    Text(BetSlipHelpers.formatOdds(odds))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Text(BetSlipHelpers.formatOdds(odds))
                    .font(.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(isSelected ? .white : .blue)
            }
            .padding()
            .background(isSelected ? Color.blue : Color(.systemGray6))
            .cornerRadius(8)
        }
        .buttonStyle(PlainButtonStyle())
    }
}
