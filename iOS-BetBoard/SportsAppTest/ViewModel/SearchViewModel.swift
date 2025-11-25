//
//  SearchViewModel.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//  Updated by Trenton Roney on 11/25/25.
//

import Foundation
import Combine

@MainActor
class SearchViewModel: ObservableObject {
    @Published var searchText = ""
    @Published var searchResults: [Team] = []
    @Published var allTeams: [Team] = []
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
            await loadTeams()
        }
    }
    
    func loadTeams() async {
        print("🔍 SearchViewModel: Starting to load teams...")
        isLoading = true
        errorMessage = nil
        
        do {
            let teams = try await firebaseService.fetchTeams()
            print("✅ SearchViewModel: Loaded \(teams.count) teams")
            
            await MainActor.run {
                self.allTeams = teams.sorted { $0.name < $1.name }
                self.isLoading = false
                
                // Print details about first few teams for debugging
                for team in teams.prefix(3) {
                    print("🏀 Team: \(team.name) (\(team.shortName))")
                    print("   Record: \(team.record.wins)-\(team.record.losses)")
                    print("   Conference: \(team.conference)")
                    if let ranking = team.ranking {
                        print("   Ranking: #\(ranking)")
                    }
                }
            }
        } catch {
            print("❌ SearchViewModel: Error loading teams: \(error)")
            await MainActor.run {
                self.errorMessage = "Failed to load teams: \(error.localizedDescription)"
                self.isLoading = false
            }
        }
    }
    
    private func performSearch(with searchText: String) {
        print("🔍 SearchViewModel: Performing search with text: '\(searchText)'")
        
        guard !searchText.isEmpty else {
            searchResults = []
            print("🔭 SearchViewModel: Empty search, clearing results")
            return
        }
        
        let searchTerms = searchText.lowercased().components(separatedBy: " ")
        print("📝 SearchViewModel: Search terms: \(searchTerms)")
        
        searchResults = allTeams.filter { team in
            let matches = searchTerms.allSatisfy { term in
                // Search in team names
                let nameMatches = team.name.lowercased().contains(term) ||
                                 team.shortName.lowercased().contains(term)
                
                // Search in conference
                let conferenceMatches = team.conference.lowercased().contains(term)
                
                // Search in nicknames
                let nicknameMatches = teamNicknames(for: team).contains { $0.lowercased().contains(term) }
                
                return nameMatches || conferenceMatches || nicknameMatches
            }
            
            if matches {
                print("✅ Match found: \(team.name)")
            }
            
            return matches
        }
        
        // Sort results: ranked teams first, then by name
        searchResults.sort { team1, team2 in
            if let rank1 = team1.ranking, let rank2 = team2.ranking {
                return rank1 < rank2
            } else if team1.ranking != nil {
                return true
            } else if team2.ranking != nil {
                return false
            } else {
                return team1.name < team2.name
            }
        }
        
        print("🎯 SearchViewModel: Found \(searchResults.count) matching results")
    }
    
    private func teamNicknames(for team: Team) -> [String] {
        switch team.shortName.uppercased() {
        case "UNC":
            return ["North Carolina", "Tar Heels", "Carolina", "Heels"]
        case "DUKE":
            return ["Duke", "Blue Devils", "Devils"]
        case "UVA", "VIRGINIA":
            return ["Virginia", "Cavaliers", "Cavs", "Wahoos"]
        case "NCSU", "NC STATE", "NCSTATE":
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
        case "KANSAS":
            return ["Kansas", "Jayhawks", "KU"]
        case "KENTUCKY", "UK":
            return ["Kentucky", "Wildcats", "UK"]
        case "GONZAGA":
            return ["Gonzaga", "Bulldogs", "Zags"]
        case "VILLANOVA", "NOVA":
            return ["Villanova", "Wildcats", "Nova"]
        case "MICHIGAN STATE", "MSU":
            return ["Michigan State", "Spartans", "MSU"]
        case "MICHIGAN":
            return ["Michigan", "Wolverines"]
        case "UCLA":
            return ["UCLA", "Bruins"]
        case "ALABAMA":
            return ["Alabama", "Crimson Tide", "Bama"]
        case "TENNESSEE":
            return ["Tennessee", "Volunteers", "Vols"]
        case "HOUSTON":
            return ["Houston", "Cougars"]
        case "PURDUE":
            return ["Purdue", "Boilermakers"]
        case "MARQUETTE":
            return ["Marquette", "Golden Eagles"]
        case "UCONN", "CONNECTICUT":
            return ["UConn", "Connecticut", "Huskies"]
        case "ARIZONA":
            return ["Arizona", "Wildcats"]
        case "BAYLOR":
            return ["Baylor", "Bears"]
        case "TEXAS":
            return ["Texas", "Longhorns"]
        default:
            return [team.name, team.shortName]
        }
    }
    
    func clearSearch() {
        searchText = ""
        searchResults = []
    }
    
    func refreshData() async {
        await loadTeams()
    }
}
