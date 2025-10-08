//
//  SearchNoResultsView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct SearchNoResultsView: View {
    var searchTerm: String = ""
    
    var body: some View {
        VStack(spacing: 28) {
            // Jordan shoe image
            Image("jordan_shoe")
                .resizable()
                .scaledToFit()
                .frame(width: 200, height: 200)
            
            // Main message
            VStack(spacing: 12) {
                Text("No Games Found!")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.primary)
                
                if !searchTerm.isEmpty {
                    Text("No games found for \"\(searchTerm)\"")
                        .font(.body)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
            }
            
            // Helpful suggestions card
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Image(systemName: "lightbulb.fill")
                        .foregroundColor(.yellow)
                    
                    Text("Try searching for:")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                
                VStack(alignment: .leading, spacing: 8) {
                    SearchSuggestionRow(
                        icon: "building.columns.fill",
                        text: "Team names",
                        examples: "Duke, UNC, Kansas"
                    )
                    
                    SearchSuggestionRow(
                        icon: "shield.fill",
                        text: "Conferences",
                        examples: "ACC, Big Ten, SEC"
                    )
                    
                    SearchSuggestionRow(
                        icon: "number",
                        text: "Rankings",
                        examples: "#1, Top 25"
                    )
                    
                    SearchSuggestionRow(
                        icon: "character.textbox",
                        text: "Abbreviations",
                        examples: "UK, UVA, FSU"
                    )
                }
            }
            .padding()
            .background(Color(.systemBackground))
            .cornerRadius(16)
            .shadow(color: .black.opacity(0.05), radius: 4)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct SearchSuggestionRow: View {
    let icon: String
    let text: String
    let examples: String
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.caption)
                .foregroundColor(.blue)
                .frame(width: 20)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(text)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(.primary)
                
                Text(examples)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
        }
    }
}

#Preview {
    SearchNoResultsView(searchTerm: "Flyers")
}
