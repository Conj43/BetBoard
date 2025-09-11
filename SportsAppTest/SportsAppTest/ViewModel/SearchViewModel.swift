//
//  SearchViewModel.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation
import Combine

@MainActor
class SearchViewModel: ObservableObject {
    @Published var searchText = ""
    @Published var searchResults: [BetSlip] = []
    @Published var allBetSlips: [BetSlip] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let firebaseService = FirebaseService()
    private var cancellables = Set<AnyCancellable>()
    
    init() {
        // Listen for search text changes with debounce
        $searchText
            .debounce(for: .milliseconds(300), scheduler: RunLoop.main)
            .sink { [weak self] searchText in
                self?.performSearch(with: searchText)
            }
            .store(in: &cancellables)
        
        // Load initial data
        Task {
            await loadBetSlips()
        }
    }
    
    func loadBetSlips() async {
        isLoading = true
        errorMessage = nil
        
        do {
            let betSlips = try await firebaseService.fetchBetSlips()
            
            await MainActor.run {
                self.allBetSlips = betSlips
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to load games: \(error.localizedDescription)"
                self.isLoading = false
            }
        }
    }
    
    private func performSearch(with searchText: String) {
        guard !searchText.isEmpty else {
            searchResults = []
            return
        }
        
        let searchTerms = searchText.lowercased().components(separatedBy: " ")
        
        searchResults = allBetSlips.filter { betSlip in
            searchTerms.allSatisfy { term in
                // Search in team names
                betSlip.homeTeam.name.lowercased().contains(term) ||
                betSlip.homeTeam.shortName.lowercased().contains(term) ||
                betSlip.awayTeam.name.lowercased().contains(term) ||
                betSlip.awayTeam.shortName.lowercased().contains(term) ||
                // Search in common abbreviations/nicknames
                teamNicknames(for: betSlip.homeTeam).contains { $0.lowercased().contains(term) } ||
                teamNicknames(for: betSlip.awayTeam).contains { $0.lowercased().contains(term) }
            }
        }
    }
    
    private func teamNicknames(for team: Team) -> [String] {
        switch team.shortName.uppercased() {
        case "UNC":
            return ["North Carolina", "Tar Heels", "Carolina", "Heels"]
        case "DUKE":
            return ["Duke", "Blue Devils", "Devils"]
        case "UVA", "VIRGINIA":
            return ["Virginia", "Cavaliers", "Cavs", "Wahoos"]
        case "NCSU", "NC STATE":
            return ["NC State", "North Carolina State", "Wolfpack", "Pack", "State"]
        case "WAKE", "WAKE FOREST":
            return ["Wake Forest", "Demon Deacons", "Deacs"]
        case "CLEMSON":
            return ["Clemson", "Tigers"]
        case "FSU", "FLORIDA STATE":
            return ["Florida State", "Seminoles", "Noles"]
        case "LOUISVILLE":
            return ["Louisville", "Cardinals", "Cards"]
        case "MIAMI":
            return ["Miami", "Hurricanes", "Canes"]
        case "PITT", "PITTSBURGH":
            return ["Pittsburgh", "Panthers", "Pitt"]
        case "SYRACUSE":
            return ["Syracuse", "Orange"]
        case "VT", "VIRGINIA TECH":
            return ["Virginia Tech", "Hokies"]
        case "BC", "BOSTON COLLEGE":
            return ["Boston College", "Eagles"]
        case "GT", "GEORGIA TECH":
            return ["Georgia Tech", "Yellow Jackets"]
        default:
            return [team.name, team.shortName]
        }
    }
    
    func clearSearch() {
        searchText = ""
        searchResults = []
    }
    
    func refreshData() async {
        await loadBetSlips()
    }
}
