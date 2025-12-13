"""
Random number generator with seed support
"""
import time


class Random:
    """Linear congruential generator matching Haxe implementation"""
    
    g = 48271.0
    n = 2147483647
    seed = 1
    
    @classmethod
    def reset(cls, seed=-1):
        """Reset random seed"""
        if seed != -1:
            cls.seed = int(seed)
        else:
            cls.seed = int(time.time() * 1000) % int(cls.n)
    
    @classmethod
    def get_seed(cls):
        """Get current seed"""
        return cls.seed
    
    @classmethod
    def _next(cls):
        """Generate next random number"""
        cls.seed = int((cls.seed * cls.g) % cls.n)
        return cls.seed
    
    @classmethod
    def float(cls):
        """Random float in [0, 1)"""
        return cls._next() / cls.n
    
    @classmethod
    def normal(cls):
        """Normalized random (average of 3 floats)"""
        return (cls.float() + cls.float() + cls.float()) / 3
    
    @classmethod
    def int(cls, min_val, max_val):
        """Random integer in [min, max)"""
        return int(min_val + cls._next() / cls.n * (max_val - min_val))
    
    @classmethod
    def bool(cls, chance=0.5):
        """Random boolean with given chance"""
        return cls.float() < chance
    
    @classmethod
    def fuzzy(cls, f=1.0):
        """Fuzzy random value"""
        if f == 0:
            return 0.5
        return (1 - f) / 2 + f * cls.normal()
