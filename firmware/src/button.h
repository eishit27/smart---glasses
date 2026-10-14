#ifndef BUTTON_H
#define BUTTON_H

enum ButtonEvent {
    EVENT_NONE = 0,
    EVENT_SINGLE_PRESS,
    EVENT_DOUBLE_PRESS,
    EVENT_TRIPLE_PRESS,
    EVENT_LONG_PRESS
};

class Button {
public:
    static void init();
    
    // Call in loop to read and debounce, returns event if one occurred
    static ButtonEvent process();
};

#endif // BUTTON_H
