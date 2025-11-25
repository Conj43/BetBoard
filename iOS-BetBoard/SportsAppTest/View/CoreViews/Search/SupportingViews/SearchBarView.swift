//
//  SearchBarView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated by Trenton Roney on 11/25/25.
//

import SwiftUI

struct SearchBarView: View {
    @Binding var searchText: String
    let onClearSearch: () -> Void
    
    var body: some View {
        HStack {
            Image(systemName: "magnifyingglass")
                .foregroundColor(.secondary)
            
            TextField("Search for teams...", text: $searchText)
                .textFieldStyle(PlainTextFieldStyle())
                .autocapitalization(.none)
                .disableAutocorrection(true)
            
            if !searchText.isEmpty {
                Button(action: onClearSearch) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
        .padding(.horizontal)
    }
}

#Preview {
    SearchBarView(searchText: .constant("Duke")) {
        // Clear action
    }
}
