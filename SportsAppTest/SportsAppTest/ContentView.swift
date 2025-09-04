//
//  ContentView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct ContentView: View {
    @StateObject private var authService = AuthService()
    
    var body: some View {
        Group {
            if authService.isSignedIn {
                TabView {
                    HomeView()
                        .tabItem {
                            Image(systemName: "house")
                            Text("Home")
                        }
                    
                    SearchView()
                        .tabItem {
                            Image(systemName: "circle")
                            Text("Search")
                        }
                    
                    PredictionsView()
                        .tabItem {
                            Image(systemName: "chart.bar.xaxis")
                            Text("Predictions")
                        }
                    AdminView()
                        .tabItem {
                            Image(systemName: "gearshape.fill")
                            Text("Admin")
                        }
                    InfoView()
                        .tabItem {
                            Image(systemName: "info.circle")
                            Text("Info")
                        }
                }
                .environmentObject(authService)
            } else {
                AuthView(authService: authService)
            }
        }
    }
}

#Preview {
    ContentView()
}
