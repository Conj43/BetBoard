//
//  SearchView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated by Trenton Roney on 11/25/25.
//

import SwiftUI

struct SearchView: View {
    @StateObject private var viewModel = SearchViewModel()
    @EnvironmentObject var authService: AuthService
    
    var body: some View {
        NavigationView {
            VStack {
                // Search Bar
                SearchBarView(
                    searchText: $viewModel.searchText,
                    onClearSearch: viewModel.clearSearch
                )
                
                // Content
                if viewModel.isLoading {
                    ProgressView("Loading teams...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let errorMessage = viewModel.errorMessage {
                    errorView(errorMessage: errorMessage)
                } else if viewModel.searchText.isEmpty {
                    SearchEmptyStateView { teamName in
                        viewModel.searchText = teamName
                    }
                } else if viewModel.searchResults.isEmpty {
                    SearchNoResultsView(searchTerm: viewModel.searchText)
                } else {
                    searchResultsList
                }
                
                Spacer()
            }
            .navigationTitle("Search")
            .refreshable {
                Task {
                    await viewModel.refreshData()
                }
            }
        }
    }
    
    // MARK: - Error View
    private func errorView(errorMessage: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundColor(.orange)
            
            Text("Error Loading Teams")
                .font(.headline)
            
            Text(errorMessage)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            Button("Try Again") {
                Task {
                    await viewModel.refreshData()
                }
            }
            .buttonStyle(.bordered)
        }
        .padding()
    }
    
    // MARK: - Search Results List
    private var searchResultsList: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(viewModel.searchResults) { team in
                    NavigationLink(destination: TeamDetailView(team: team)) {
                        TeamSearchResultRowView(team: team)
                    }
                    .buttonStyle(PlainButtonStyle())
                }
            }
            .padding(.horizontal)
        }
    }
}

#Preview {
    SearchView()
        .environmentObject(AuthService())
}
