import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { StatusBar } from 'expo-status-bar';

export default function App() {
  const [count, setCount] = useState(0);

  const handlePress = () => {
    setCount(count + 1);
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      <View style={styles.header}>
        <Text style={styles.title}>Ma Premier App</Text>
        <Text style={styles.subtitle}>Application Mobile Native</Text>
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Bienvenue sur votre app mobile! 📱</Text>
          <Text style={styles.cardText}>
            Cette application est créée avec React Native et peut être compilée en app iOS et Android natives.
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Compteur Interactif</Text>
          <View style={styles.counterContainer}>
            <Text style={styles.counterText}>{count}</Text>
          </View>
          <TouchableOpacity style={styles.button} onPress={handlePress}>
            <Text style={styles.buttonText}>Appuyez-moi</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Prochaines étapes</Text>
          <Text style={styles.feature}>✓ Installer l'app sur votre téléphone</Text>
          <Text style={styles.feature}>✓ Utiliser des capteurs (caméra, GPS, etc.)</Text>
          <Text style={styles.feature}>✓ Ajouter plusieurs écrans avec navigation</Text>
          <Text style={styles.feature}>✓ Connecter à une base de données</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Pour compiler l'app</Text>
          <Text style={styles.code}>npm run build-android</Text>
          <Text style={styles.code}>npm run build-ios</Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    backgroundColor: '#007AFF',
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 5,
  },
  content: {
    flex: 1,
    padding: 15,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1a1a1a',
    marginBottom: 10,
  },
  cardText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  counterContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 20,
  },
  counterText: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  button: {
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  feature: {
    fontSize: 14,
    color: '#333',
    marginVertical: 6,
    lineHeight: 20,
  },
  code: {
    fontSize: 12,
    color: '#007AFF',
    backgroundColor: '#f5f5f5',
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 4,
    marginVertical: 5,
    fontFamily: 'Courier New',
  },
});
