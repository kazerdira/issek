import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated } from 'react-native';
import { colors } from '../theme/colors';

interface TypingIndicatorProps {
  size?: number;
  dotColor?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ 
  size = 8, 
  dotColor = colors.textSecondary 
}) => {
  const dot1Anim = useRef(new Animated.Value(0)).current;
  const dot2Anim = useRef(new Animated.Value(0)).current;
  const dot3Anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const createAnimation = (animValue: Animated.Value, delay: number) => {
      return Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(animValue, {
            toValue: 1,
            duration: 400,
            useNativeDriver: true,
          }),
          Animated.timing(animValue, {
            toValue: 0,
            duration: 400,
            useNativeDriver: true,
          }),
        ])
      );
    };

    const animation1 = createAnimation(dot1Anim, 0);
    const animation2 = createAnimation(dot2Anim, 200);
    const animation3 = createAnimation(dot3Anim, 400);

    animation1.start();
    animation2.start();
    animation3.start();

    return () => {
      animation1.stop();
      animation2.stop();
      animation3.stop();
    };
  }, []);

  const dotStyle = (animValue: Animated.Value) => ({
    width: size,
    height: size,
    borderRadius: size / 2,
    backgroundColor: dotColor,
    marginHorizontal: 2,
    opacity: animValue.interpolate({
      inputRange: [0, 1],
      outputRange: [0.3, 1],
    }),
    transform: [
      {
        translateY: animValue.interpolate({
          inputRange: [0, 1],
          outputRange: [0, -size / 2],
        }),
      },
    ],
  });

  return (
    <View style={styles.container}>
      <Animated.View style={dotStyle(dot1Anim)} />
      <Animated.View style={dotStyle(dot2Anim)} />
      <Animated.View style={dotStyle(dot3Anim)} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
