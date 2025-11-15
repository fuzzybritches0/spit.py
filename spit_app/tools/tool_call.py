# SPDX-License-Identifier: GPL-2.0
class Tool:
    def call(self, tool_call: dict) -> dict:
        return {"role": "tool",
                "tool_call_id": tool_call["id"],
                "name": tool_call["function"]["name"],
                "content": '{"unit":"celsius","temperature":3}'
                }
