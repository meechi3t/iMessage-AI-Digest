-- Send a message via iMessage
-- Usage: osascript send_imessage.scpt <target> <message>
-- target: chat GUID (for group chats) or phone number like +15551234567

on run argv
    set targetID to item 1 of argv
    set messageText to item 2 of argv

    tell application "Messages"
        if targetID starts with "chat" or targetID starts with "any" or targetID starts with "iMessage" then
            -- Group chat via GUID
            set targetChat to chat id targetID
            send messageText to targetChat
        else
            -- Individual via phone number
            send messageText to participant targetID
        end if
    end tell
end run
