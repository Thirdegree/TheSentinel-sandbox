#SOMETHING TO HANDLE REDDIT'S BULLSHIT

class InvalidAddition(Exception):
    def __init__(self, *args, **kwargs):
        super(InvalidAddition, self).__init__(*args, **kwargs)
        

class TooFrequent(Exception):
    def __init__(self, waitTime, *args, **kwargs):
        super(TooFrequent, self).__init__(*args, **kwargs)
        self.waitTime = waitTime.seconds//60 + 1

