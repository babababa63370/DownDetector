import { Text, View, Button, StyleSheet } from 'react-native';
import { useState } from 'react';

export default function App() {
  const [count, setCount] = useState(0);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Ma Premier App</Text>
      <Text style={styles.count}>{count}</Text>
      <Button title="Appuyez-moi" onPress={() => setCount(count + 1)} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 32,
    marginBottom: 20,
  },
  count: {
    fontSize: 60,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 20,
  },
});
