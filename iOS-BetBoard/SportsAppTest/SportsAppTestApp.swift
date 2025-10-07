

//
//  SportsAppTestApp.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/1/25.
//


import SwiftUI
import Firebase

@main
struct SportsAppTestApp: App {
    
    init() {
        FirebaseApp.configure()
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
